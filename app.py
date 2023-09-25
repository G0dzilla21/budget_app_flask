import os
from bson import ObjectId
from flask import Flask, json, render_template, request, redirect, session, jsonify, url_for, flash, get_flashed_messages
from flask_bcrypt import Bcrypt
from flask_session import Session
from mongo_connect import client
import requests
from dotenv import load_dotenv #pip install python-dotenv
from bson import json_util
from datetime import datetime, timedelta

from collections import defaultdict


app = Flask(__name__)
load_dotenv()

app.config["API_SECRET_KEY"] = "api_secret_key"
app.config["SESSION_TYPE"] = "filesystem"

bcrypt = Bcrypt(app)
Session(app)

db = client["Budgets_Flask"]
test_db = client["Budgets_Test"]

# For budget data
budgets_collection = db["budgets"]

# For user data
users_collection = db["users"]

# For user subscription data
subscriptions_collection = db['subscriptions']  
test_subscriptions_collection = test_db['subscriptions']

# chatbot api key
api_secret_key = os.getenv("GPT_SECRET_KEY")

# chatbot api key
api_secret_key = os.getenv("GPT_SECRET_KEY")




def nav_menu():
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        return render_template("nav_menu.html", username=user["username"])

@app.route("/dashboard")
def dashboard():
    # Ensure user is logged in
    if "user_id" not in session:
        return redirect("/login")

    # Retrieve the budgets associated with the logged-in user
    budgets = list(budgets_collection.find({"user_id": session["user_id"]}))
    
    # Extract data for chart from the budgets list
    budget_names = [budget['name'] for budget in budgets if budget.get('isActive', False)]
    budget_amounts = [budget['amount'] for budget in budgets if budget.get('isActive', False)]
    budget_totals = [budget.get('total', 0) for budget in budgets if budget.get('isActive', False)]
    print(budget_names)
    # Now pass these to the template
    return render_template("chart.html", 
                           budgets=budgets,
                           budget_names=budget_names,
                           budget_amounts=budget_amounts,
                           budget_totals=budget_totals, user_logged_in=True)


@app.route("/")
def index():
    """Renders the index page."""
    if "user_id" in session:
        try:
            update_budget_activity_status()
        except:
            flash("Problem updating budget statuses.", 'info')
        user = db.users.find_one({"_id": session["user_id"]})
        user_budgets = list(budgets_collection.find({"user_id": session["user_id"]}))
        
        return render_template("index.html", user=user, user_logged_in=True, budgets=user_budgets, api_secret_key=api_secret_key)
    return render_template("index.html", user_logged_in=False, api_secret_key=api_secret_key)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        db.users.insert_one({"username": username, "password": hashed_password, "email": email})
        return redirect("/login")
    return render_template("register.html", message=None)  # Pass a message to the template if needed

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = db.users.find_one({"username": username})
        if user and bcrypt.check_password_hash(user["password"], password):
            session["user_id"] = user["_id"]
            return redirect("/")
        else:
            message = "Invalid username or password"  # Add an error message if login fails
            return render_template("login.html", message=message)
    return render_template("login.html", message=None)

@app.route("/logout")
def logout():
    session.clear()  # Clear the user's session data
    return render_template("logout.html")


@app.route("/profile")
def profile():
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        return render_template("profile.html", username=user["username"], user_logged_in=True)
    return redirect("/login")

@app.route("/update_password", methods=["POST"])
def update_password():
    if "user_id" in session:
        if request.method == "POST":
            current_password = request.form["current_password"]
            new_password = request.form["new_password"]
            confirm_new_password = request.form["confirm_new_password"]
            user = db.users.find_one({"_id": session["user_id"]})
            
            if bcrypt.check_password_hash(user["password"], current_password):
            
                if new_password == confirm_new_password:
                    # Hash and update the new password in the database
                    hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")
                    db.users.update_one(
                        {"_id": session["user_id"]},
                        {"$set": {"password": hashed_password}}
                    )
                    # Pass a success message to the template
                    success_message = "Password changed successfully."
                    return render_template("profile.html", username=user["username"], success_message=success_message, user_logged_in=True)
                else:
                    error_message = "New password and confirmation do not match."
                    return render_template("profile.html", username=user["username"], error_message=error_message, user_logged_in=True)
            else:
                error_message = "Current password is incorrect."
                return render_template("profile.html", username=user["username"], error_message=error_message, user_logged_in=True)
        return redirect("/login")   

@app.route("/create_budget", methods=["POST"])
def create_budget():
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        username = user['username']
        budget_name = request.form["budget_name"]
        budget_amount = float(request.form["budget_amount"])
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        category = request.form["budget_category"]
        

        if start_date <= end_date:
            budgets_collection.insert_one({
                "user_id": session["user_id"],
                "name": budget_name,
                "amount": budget_amount,
                "date_created": datetime.utcnow(),
                "created_by": username,
                "startDate": start_date,
                "endDate": end_date,
                "category":  category,
                "isActive": True,
                "total": 0,
                "transactions": []
                })
        elif start_date > end_date:
            flash(u'Failed to add Budget... Confirm that your start date is before your end date.', 'info')

    
        return redirect("/")
    else:
        return redirect("/login")
    
@app.route("/delete_budget/<budget_id>")
def delete_budget(budget_id):
    if "user_id" in session:
        budgets_collection.delete_one({"_id": ObjectId(budget_id), "user_id": session["user_id"]})
        return redirect("/")
    else:
        return redirect("/login")


@app.route("/edit_budget/<budget_id>")
def edit_budget_form(budget_id):
    if "user_id" in session:
        budget = budgets_collection.find_one({"_id": ObjectId(budget_id), "user_id": session["user_id"]})
        if budget:
            return render_template("edit_budget.html", budget=budget)
    return redirect("/")

@app.route("/update_budget/<budget_id>", methods=["POST"])
def update_budget(budget_id):
    if "user_id" in session:
        new_name = request.form["budget_name"]
        new_amount = float(request.form["budget_amount"])
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        category = request.form["budget_category"]
        
        budgets_collection.update_one(
            {"_id": ObjectId(budget_id), "user_id": session["user_id"]},
            {"$set": {
                "name": new_name,
                "amount": new_amount,
                "startDate": start_date,
                "endDate": end_date,
                "category":  category,
            }}
        )
        
        return redirect("/")
    else:
        return redirect("/login")


@app.route("/add_transaction/<budget_id>", methods=["POST"])
def add_transaction(budget_id):
    if "user_id" in session:
        item = request.form["transaction_item"]
        amount = float(request.form["transaction_amount"])
        budget = budgets_collection.find_one({"_id": ObjectId(budget_id), "user_id": session["user_id"]})
        if not budget:
            return redirect("/")

        # Calculate the total of existing transactions
        existing_transactions_total = sum(trans["amount"] for trans in budget["transactions"])

        # Validate the new transaction
        if amount < 0 or (existing_transactions_total + amount) > budget["amount"]:
            flash(u'Failed: You are attempting a transaction that will surpass your budget!', 'info')
            return redirect(f"/manage_transactions/{ObjectId(budget_id)}")

        # Add the new transaction
        new_transaction = {
        "item": item,
        "amount": amount,
        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        new_total = budget.get("total", 0) + amount
        budgets_collection.update_one({"_id": ObjectId(budget_id), "user_id": session["user_id"]},
                                      {"$set": {"total": new_total}, "$push": {"transactions": new_transaction}})       
    return redirect(f"/manage_transactions/{ObjectId(budget_id)}")

@app.route("/remove_transaction/<budget_id>/<transaction_index>", methods=["GET"])
def remove_transaction(budget_id, transaction_index):
    if "user_id" in session:
        budget = budgets_collection.find_one({"_id": ObjectId(budget_id), "user_id": session["user_id"]})
        if not budget:
            return redirect("/")
        
        # Get the transaction to remove
        transaction_to_remove = budget["transactions"][int(transaction_index)]
        
        # Update the "total" and remove the transaction
        new_total = budget.get("total", 0) - transaction_to_remove["amount"]
        budgets_collection.update_one(
            {"_id": ObjectId(budget_id), "user_id": session["user_id"]},
            {
                "$set": {"total": new_total},
                "$pull": {"transactions": transaction_to_remove}
            }
        )
    return redirect(f"/manage_transactions/{ObjectId(budget_id)}")

@app.route("/manage_transactions/<budget_id>")
def manage_transactions(budget_id):
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        budget = budgets_collection.find_one({"_id": ObjectId(budget_id), "user_id": session["user_id"]})

        if not budget:
            flash("Budget not found", "error")
            return redirect("/")

        # Extract data for the chart from the budget
        budget_names = [budget['name']]
        budget_amounts = [budget['amount']]
        budget_totals = [budget.get('total', 0)]

        return render_template("manage_transactions.html", 
                               user=user, 
                               budget=budget, 
                               user_logged_in=True,
                               budget_names=budget_names,
                               budget_amounts=budget_amounts,
                               budget_totals=budget_totals)

@app.route('/subscriptions', methods=['GET', 'POST'])
def subscriptions():
    if "user_id" not in session:
        # Not logged in, redirect to the login page or an error page
        return redirect(url_for('login'))
    else:

        if request.method == 'POST':
            # Process the subscription form data
            name = request.form.get("name")
            amount = request.form.get("amount")
            billing_cycle = request.form.get("billing_cycle")
            start_date = request.form.get("start_date")

            subscription_data = {
                "user_id": session["user_id"],
                "name": name,
                "amount": amount,
                "billing_cycle": billing_cycle,
                "start_date": start_date
            }

            subscriptions_collection.insert_one(subscription_data)

        # Pull subscriptions for this user and calculate renewals
        all_subscriptions = list(subscriptions_collection.find({"user_id": session["user_id"]}))
        upcoming_renewals = [sub for sub in all_subscriptions if is_upcoming(sub)]
        regular_subscriptions = [sub for sub in all_subscriptions if sub not in upcoming_renewals]

        return render_template('subscriptions.html', upcoming=upcoming_renewals, regular=regular_subscriptions, user_logged_in=True, api_secret_key=api_secret_key)

def is_upcoming(subscriptions_collection):
    today = datetime.today()
    seven_days_from_now = today + timedelta(days=7)
    
    # Assuming 'frequency' could be 'monthly', 'annual', etc.
    if subscriptions_collection['renewal_frequency'] == 'monthly':
        renewal_date = subscriptions_collection['start_date'] + timedelta(days=30)  # Adjust for exact duration if needed
    elif subscriptions_collection['renewal_frequency'] == 'annually':
        renewal_date = subscriptions_collection['start_date'] + timedelta(days=365)  # Adjust for leap years if necessary
    
    # Add more frequency conditions as needed
    
    # The logic for checking if it's upcoming
    return today <= renewal_date <= seven_days_from_now



@app.route("/add_subscription", methods=["POST"])
def add_subscription():
    if "user_id" not in session:
        return redirect(url_for('login'))  # or wherever your login page is

    name = request.form.get("name")
    amount = float(request.form.get("amount"))
    start_date = datetime.strptime(request.form.get("start_date"), '%Y-%m-%d')
    
    renewal_frequency = request.form.get("renewal_frequency")
    if renewal_frequency == "monthly":
        next_renewal_date = start_date + timedelta(days=30)
    elif renewal_frequency == "annually":
        next_renewal_date = start_date + timedelta(days=365)
    # ... handle other frequencies as needed

    new_subscription = {
        "user_id": session["user_id"],
        "name": name,
        "amount": amount,
        "start_date": start_date,
        "renewal_frequency": renewal_frequency,
        "next_renewal_date": next_renewal_date
    }

    subscriptions_collection.insert_one(new_subscription)

    flash('Successfully added subscription', 'success')
    return redirect(url_for('subscriptions'))

@app.route("/delete_subscription/<subscription_id>", methods=["GET","POST", "DELETE"])
def delete_subscription(subscription_id):
    if "user_id" not in session:
        return redirect(url_for('login'))
    
    # Remove the subscription with the provided ID
    subscriptions_collection.delete_one({"_id": ObjectId(subscription_id), "user_id": session["user_id"]})
    
    flash('Successfully deleted subscription', 'success')  # 'success' is an optional category
    return redirect(url_for('subscriptions'))

@app.route("/edit_subscription/<subscription_id>", methods=["GET"])
def edit_subscription_form(subscription_id):
    if "user_id" not in session:
        return redirect(url_for('login'))
    
    # Fetch the subscription to be edited
    subscription = subscriptions_collection.find_one({"_id": ObjectId(subscription_id), "user_id": session["user_id"]})
    
    if not subscription:
        return "Subscription not found!", 404
    
    return render_template("edit_subscription.html", subscription=subscription)

@app.route("/edit_subscription/<subscription_id>", methods=["POST"])
def edit_subscription(subscription_id):
    if "user_id" not in session:
        return redirect(url_for('login'))
    
    name = request.form.get("name")
    amount = float(request.form.get("amount"))
    start_date = datetime.strptime(request.form.get("start_date"), '%Y-%m-%d')
    renewal_frequency = request.form.get("renewal_frequency")
    
    if renewal_frequency == "monthly":
        next_renewal_date = start_date + timedelta(days=30)
    elif renewal_frequency == "annually":
        next_renewal_date = start_date + timedelta(days=365)
    # ... handle other frequencies as needed

    updated_subscription = {
        "$set": {
            "name": name,
            "amount": amount,
            "start_date": start_date,
            "renewal_frequency": renewal_frequency,
            "next_renewal_date": next_renewal_date
        }
    }
    
    # Update the subscription
    subscriptions_collection.update_one({"_id": ObjectId(subscription_id), "user_id": session["user_id"]}, updated_subscription)
    
    flash('Successfully edited subscription', 'success')  # 'success' is an optional category
    return redirect(url_for('subscriptions'))




# @app.route('/')
# def chat_gpt():
#     return render_template('chat-gpt.html', api_secret_key=api_secret_key)    

#function for updating budget status
def update_budget_activity_status():
    current_date = datetime.utcnow()
    budgets = budgets_collection.find()
    for budget in budgets:
        end_date = datetime.strptime(str(budget["endDate"]), "%Y-%m-%d")
        is_active = current_date < (end_date + timedelta(days=1))
        budgets_collection.update_one({"_id": budget["_id"]}, {"$set": {"isActive": is_active}})

if __name__ == "__main__":
    app.run(debug=True)
 