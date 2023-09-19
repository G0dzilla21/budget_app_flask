import os
from bson import ObjectId
from flask import Flask, json, render_template, request, redirect, session, jsonify
from flask_bcrypt import Bcrypt
from flask_session import Session
from mongo_connect import client
import requests
from dotenv import load_dotenv #pip install python-dotenv
from bson import json_util
from datetime import datetime

from collections import defaultdict

load_dotenv()

app = Flask(__name__, static_url_path='/static')
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SESSION_TYPE"] = "filesystem"

bcrypt = Bcrypt(app)
Session(app)

db = client["Budgets_Flask"]

# For budget data
budgets_collection = db["budgets"]

# For user data
users_collection = db["users"]


@app.route("/")
def index():
    """Renders the index page."""
    if "user_id" in session:
        user = db.users.find_one({"_id": session["user_id"]})
        user_budgets = list(budgets_collection.find({"user_id": session["user_id"]}))
        return render_template("index.html", user=user, user_logged_in=True, budgets=user_budgets)
    return render_template("index.html", user_logged_in=False)


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
        budget_name = request.form["budget_name"]
        budget_amount = float(request.form["budget_amount"])
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        category = request.form["budget_category"]
        
        budgets_collection.insert_one({
            "user_id": session["user_id"],
            "name": budget_name,
            "amount": budget_amount,
            "date_created": datetime.utcnow(),
            "startDate": start_date,
            "endDate": end_date,
            "category":  category,
            "transactions": []
    })
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
                "transactions": []
            }}
        )
        
        return redirect("/")
    else:
        return redirect("/login")

         


if __name__ == "__main__":
    app.run(debug=True)
 