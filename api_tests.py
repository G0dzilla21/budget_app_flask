import unittest
from app import app, test_db, bcrypt
from unittest.mock import patch
from datetime import datetime
from bson import ObjectId
from app import test_subscriptions_collection

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()

        # Mock database setup, storing password as plain text for testing purposes
        self.user_data = {
            'username': 'testuser',
            'password': 'testpassword',  # plain text password for testing
            'email': 'test@example.com'
        }
        test_db.users.insert_one(self.user_data)

    def tearDown(self):
        test_db.users.delete_one({'username': 'testuser'})

    def test_register(self):
        new_user_data = {
            'username': 'newtestuser',
            'password': 'newtestpassword',  # plain text password for testing
            'email': 'newtest@example.com',
        }
        response = self.client.post('/register', data=new_user_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Register', response.data)

        # Cleanup: remove the newly registered user
        test_db.users.delete_one({'username': 'newtestuser'})

    @patch('app.bcrypt.check_password_hash')
    def test_login(self, mock_check):
        mock_check.return_value = True

        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'  # the plain text password
        })
        self.assertEqual(response.status_code, 200)

    
    @patch('app.bcrypt.check_password_hash')
    def test_invalid_login(self, mock_check):
        mock_check.return_value = False

        response = self.client.post('/login', data={
            'username': 'invaliduser',
            'password': 'invalidpassword'  # the plain text password
        })
        self.assertNotEqual(response.status_code, 302)
        self.assertIn(b'Invalid username or password', response.data)  # Assuming this error message appears in the rendered HTML

    def test_index(self):
        response = self.client.get('/')
        self.assertIn(b'You are not logged in.', response.data)

    def test_logout(self):
    # Assuming the user is logged in at this point
        self.client.get('/logout')
        response = self.client.get('/profile')
        self.assertNotEqual(response.status_code, 200) # Expecting a redirect, which is status code 302

    def test_profile_logged_out(self):
        # Assuming the user is not logged in
        response = self.client.get('/profile')
        self.assertNotEqual(response.status_code, 200) # Expecting a redirect to login page


    #  more api route unit testing here
    @patch('app.bcrypt.check_password_hash')    
    def test_create_budget(self, mock_check):
        
        mock_check.return_value = True
        # Logging in as a user
        with self.client:
            self.client.post('/login', data=dict(
                username="testuser",
                password="testpassword"
            ), follow_redirects=True)
            
            response = self.client.post('/create_budget', data=dict(
                budget_name="Test Budget",
                budget_amount="1000",
                start_date=str(datetime.utcnow()),
                end_date="2024-01-01",
                budget_category="Test Category",
            ), follow_redirects=True)

            budget_data = {
                "budget_name": "Test Budget",
                "budget_amount": "1000",
                "start_date": "2023-01-01",
                "end_date": "2024-01-01",
                "budget_category": "Test Category"
            }



        response = self.client.post('/create_budget', data=budget_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Cleanup: remove the newly created budget (if needed)
        # Replace 'user_id_here' and 'Test Budget' with actual data to locate and delete the budget

    def test_delete_budget(self):
        # Assuming the user is logged in and there's a budget to delete
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'user_id_here'  # Set a mock user ID

        # Create a mock budget to delete
        mock_budget = {
            'user_id': 'user_id_here',
            'name': 'Budget to Delete',
            # Other budget data...
        }
        test_db.budgets.insert_one(mock_budget)

        # Get the ID of the mock budget to delete
        budget_id_to_delete = test_db.budgets.find_one({'name': 'Budget to Delete'})['_id']

        response = self.client.get(f'/delete_budget/{budget_id_to_delete}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Budget to Delete', response.data)  # Check if the budget name is not in the response

        # Cleanup: remove the mock budget if needed

    '''
    def test_update_budget(self):
        # Log in the user and set session (replace with your actual login code)
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 'some_user_id'  # Set user_id in the session
                
        # Create a budget (replace with your actual budget creation code)
        budget_id = test_db.budgets.insert_one({
            "user_id": 'some_user_id',
            "name": 'Old Budget Name',
            "amount": 100,
            "startDate": "2023-01-01",
            "endDate": "2023-12-31",
            "category": "Old Category",
        }).inserted_id
        
        # Send POST request to update the budget
        response = self.client.post(f'/update_budget/{budget_id}', data={
            "budget_name": "New Budget Name",
            "budget_amount": 200,
            "start_date": "2023-02-01",
            "end_date": "2023-11-30",
            "budget_category": "New Category"
        })

        # Check the response (optional, e.g., you may want to check for a redirect to '/')
        self.assertEqual(response.status_code, 302)  # Assuming it redirects to home
        
        # Query the database to ensure the budget was successfully updated
        updated_budget = test_db.budgets.find_one({"_id": ObjectId(budget_id)})
        self.assertEqual(updated_budget["amount"], 200)

    def test_add_transaction(self):
        # Log in the user and set session (replace with your actual login code)
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 'some_user_id'  # Set user_id in the session
                
        # Create a budget (replace with your actual budget creation code)
        budget_id = test_db.budgets.insert_one({
            "user_id": 'some_user_id',
            "name": 'Test Budget',
            "amount": 1000,
            "startDate": "2023-01-01",
            "endDate": "2023-12-31",
            "category": "Test Category",
            "total": 0,
            "transactions": []
        }).inserted_id
        
        # Send POST request to add a transaction to the budget
        response = self.client.post(f'/add_transaction/{budget_id}', data={
            "transaction_item": "Test Item",
            "transaction_amount": 200
        })

        # Check the response (optional, e.g., you may want to check for a redirect to '/')
        self.assertEqual(response.status_code, 302)  # Assuming it redirects to home
        
        # Query the database to ensure the transaction was successfully added
        updated_budget = test_db.budgets.find_one({"_id": ObjectId(budget_id)})
        self.assertEqual(len(updated_budget["transactions"]), 1)  # 1 transaction has been added
        self.assertEqual(updated_budget["transactions"][0]["item"], "Test Item")
        self.assertEqual(updated_budget["transactions"][0]["amount"], 200)

    def test_remove_transaction(self):
        # Log in the user and set session (replace with your actual login code)
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 'some_user_id'  # Set user_id in the session
                
        # Create a budget with a transaction (replace with your actual budget creation code)
        budget_id = test_db.budgets.insert_one({
            "user_id": 'some_user_id',
            "name": 'Test Budget',
            "amount": 1000,
            "startDate": "2023-01-01",
            "endDate": "2023-12-31",
            "category": "Test Category",
            "total": 200,
            "transactions": [
                {"item": "Test Item", "amount": 200, "date": "2023-01-01 01:01:01"}
            ]
        }).inserted_id
        
        # Send GET request to remove a transaction from the budget
        response = self.client.get(f'/remove_transaction/{budget_id}/0')

        # Check the response (optional, e.g., you may want to check for a redirect to '/')
        self.assertEqual(response.status_code, 302)  # Assuming it redirects to home
        
        # Query the database to ensure the transaction was successfully removed
        updated_budget = test_db.budgets.find_one({"_id": ObjectId(budget_id)})
        self.assertEqual(len(updated_budget["transactions"]), 0)  # No transactions should be present
        self.assertEqual(updated_budget["total"], 0)  # Total should be 0 after removing the transaction
    '''

    def test_subscriptions(self):
        # Assuming the user is logged in
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'user_id_here'  # Set a mock user ID

        response = self.client.get('/subscriptions')
        self.assertEqual(response.status_code, 200)

        # You can add assertions to check for specific data in the response if needed

    def test_add_subscription(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 'some_user_id'  # Assuming your session has a user_id

            response = self.client.post('/add_subscription', data={
                'name': 'Netflix',
                'amount': '9.99',
                'start_date': '2023-01-01',
                'renewal_frequency': 'monthly'
            })

            self.assertEqual(response.status_code, 302)  # Assuming it redirects
            subscription = test_subscriptions_collection.find_one({'name': 'Netflix'})
            self.assertIsNotNone(subscription)

    '''
    def test_delete_subscription(self):
        # First, add a subscription to the database to delete later
        subscription_id = test_subscriptions_collection.insert_one({
            'user_id': 'some_user_id',
            'name': 'Netflix',
            'amount': 9.99
        }).inserted_id

        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 'some_user_id'

            response = self.client.delete(f'/delete_subscription/{subscription_id}')
            self.assertEqual(response.status_code, 302)  # Assuming it redirects

            # Now check that the subscription was actually deleted
            subscription = test_subscriptions_collection.find_one({'_id': subscription_id})
            self.assertIsNone(subscription)
    '''

if __name__ == '__main__':
    unittest.main()
    
