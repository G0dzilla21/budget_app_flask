import unittest
from app import app, db, bcrypt
from unittest.mock import patch

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
        db.users.insert_one(self.user_data)

    def tearDown(self):
        db.users.delete_one({'username': 'testuser'})

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
        db.users.delete_one({'username': 'newtestuser'})

    @patch('app.bcrypt.check_password_hash')
    def test_login(self, mock_check):
        mock_check.return_value = True

        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'  # the plain text password
        })
        self.assertEqual(response.status_code, 302)

    
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
    def test_create_budget(self):
        # Assuming the user is logged in
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'user_id_here'  # Set a mock user ID

        budget_data = {
            'budget_name': 'Test Budget',
            'budget_amount': '1000',
            'start_date': '2023-09-21',
            'end_date': '2023-09-30',
            'budget_category': 'Test Category'
        }

        response = self.client.post('/create_budget', data=budget_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Budget', response.data)  # Check if the budget name appears in the response

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
        db.budgets.insert_one(mock_budget)

        # Get the ID of the mock budget to delete
        budget_id_to_delete = db.budgets.find_one({'name': 'Budget to Delete'})['_id']

        response = self.client.get(f'/delete_budget/{budget_id_to_delete}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Budget to Delete', response.data)  # Check if the budget name is not in the response

        # Cleanup: remove the mock budget if needed

    @patch('app.budgets_collection.update_one')  # Mock the update operation
    def test_update_budget(self, mock_update):
        # Assuming the user is logged in
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'user_id_here'  # Set a mock user ID

        # Create a mock budget to update
        mock_budget = {
            'user_id': 'user_id_here',
            'name': 'Budget to Update',
            # Other budget data...
        }
        db.budgets.insert_one(mock_budget)

        # Get the ID of the mock budget to update
        budget_id_to_update = db.budgets.find_one({'name': 'Budget to Update'})['_id']

        updated_budget_data = {
            'budget_name': 'Updated Budget Name',
            'budget_amount': '1500',
            'start_date': '2023-09-22',
            'end_date': '2023-09-30',
            'budget_category': 'Updated Category'
        }

        response = self.client.post(f'/update_budget/{budget_id_to_update}', data=updated_budget_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check if the update operation was called with the expected arguments
        mock_update.assert_called_with(
            {'_id': budget_id_to_update, 'user_id': 'user_id_here'},
            {
                '$set': {
                    'name': 'Updated Budget Name',
                    'amount': 1500.0,
                    'startDate': '2023-09-22',
                    'endDate': '2023-09-30',
                    'category': 'Updated Category'
                }
            }
        )

    @patch('app.budgets_collection.find_one')
    @patch('app.budgets_collection.update_one')
    def test_add_transaction(self, mock_update, mock_find_one):
        # Assuming the user is logged in and there's a budget to add a transaction to
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'user_id_here'  # Set a mock user ID

        # Create a mock budget to add a transaction to
        mock_budget = {
            '_id': 'budget_id_here',
            'user_id': 'user_id_here',
            'name': 'Test Budget',
            'amount': 1000.0,
            'transactions': [],
            # Other budget data...
        }
        mock_find_one.return_value = mock_budget

        transaction_data = {
            'transaction_item': 'Item 1',
            'transaction_amount': '50',
        }

        response = self.client.post('/add_transaction/budget_id_here', data=transaction_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check if the update operation was called with the expected arguments
        mock_update.assert_called_with(
            {'_id': 'budget_id_here', 'user_id': 'user_id_here'},
            {
                '$set': {'total': 50.0},
                '$push': {'transactions': {'item': 'Item 1', 'amount': 50.0, 'date': mock.ANY}}
            }
        )

        # Cleanup: remove the mock budget if needed

    @patch('app.budgets_collection.find_one')
    @patch('app.budgets_collection.update_one')
    def test_remove_transaction(self, mock_update, mock_find_one):
        # Assuming the user is logged in and there's a budget with a transaction to remove
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'user_id_here'  # Set a mock user ID

        # Create a mock budget with a transaction to remove
        mock_budget = {
            '_id': 'budget_id_here',
            'user_id': 'user_id_here',
            'name': 'Test Budget',
            'amount': 1000.0,
            'transactions': [{'item': 'Item 1', 'amount': 50.0, 'date': '2023-09-21 12:00:00'}],
            # Other budget data...
        }
        mock_find_one.return_value = mock_budget

        response = self.client.get('/remove_transaction/budget_id_here/0', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check if the update operation was called with the expected arguments
        mock_update.assert_called_with(
            {'_id': 'budget_id_here', 'user_id': 'user_id_here'},
            {
                '$set': {'total': 0.0},
                '$pull': {'transactions': {'item': 'Item 1', 'amount': 50.0, 'date': '2023-09-21 12:00:00'}}
            }
        )

        # Cleanup: remove the mock budget if needed

    def test_subscriptions(self):
        # Assuming the user is logged in
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'user_id_here'  # Set a mock user ID

        response = self.client.get('/subscriptions')
        self.assertEqual(response.status_code, 200)

        # You can add assertions to check for specific data in the response if needed

    @patch('app.subscriptions_collection.insert_one')
    def test_add_subscription(self, mock_insert_one):
        # Assuming the user is logged in
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'user_id_here'  # Set a mock user ID

        subscription_data = {
            'name': 'Test Subscription',
            'amount': '50',
            'start_date': '2023-09-21',
            'renewal_frequency': 'monthly',
        }

        response = self.client.post('/add_subscription', data=subscription_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check if the insert operation was called with the expected arguments
        mock_insert_one.assert_called_with({
            'user_id': 'user_id_here',
            'name': 'Test Subscription',
            'amount': 50.0,
            'start_date': '2023-09-21',
            'renewal_frequency': 'monthly',
        })

        # Cleanup: remove the mock subscription if needed

    @patch('app.subscriptions_collection.delete_one')
    def test_delete_subscription(self, mock_delete_one):
        # Assuming the user is logged in and there's a subscription to delete
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'user_id_here'  # Set a mock user ID

        # Create a mock subscription to delete
        mock_subscription = {
            '_id': 'subscription_id_here',
            'user_id': 'user_id_here',
            'name': 'Test Subscription',
            # Other subscription data...
        }

        response = self.client.get('/delete_subscription/subscription_id_here', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check if the delete operation was called with the expected arguments
        mock_delete_one.assert_called_with({'_id': 'subscription_id_here', 'user_id': 'user_id_here'})

        # Cleanup: remove the mock subscription if needed

    @patch('app.subscriptions_collection.find_one')
    @patch('app.subscriptions_collection.update_one')
    def test_edit_subscription(self, mock_update, mock_find_one):
        # Assuming the user is logged in and there's a subscription to edit
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'user_id_here'  # Set a mock user ID

        # Create a mock subscription to edit
        mock_subscription = {
            '_id': 'subscription_id_here',
            'user_id': 'user_id_here',
            'name': 'Test Subscription',
            'amount': 50.0,
            'start_date': '2023-09-21',
            'renewal_frequency': 'monthly',
            # Other subscription data...
        }
        mock_find_one.return_value = mock_subscription

        updated_subscription_data = {
            'name': 'Updated Subscription',
            'amount': '75',
            'start_date': '2023-09-22',
            'renewal_frequency': 'annually',
        }

        response = self.client.post('/edit_subscription/subscription_id_here', data=updated_subscription_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check if the update operation was called with the expected arguments
        mock_update.assert_called_with(
            {'_id': 'subscription_id_here', 'user_id': 'user_id_here'},
            {
                '$set': {
                    'name': 'Updated Subscription',
                    'amount': 75.0,
                    'start_date': '2023-09-22',
                    'renewal_frequency': 'annually',
                }
            }
        )

if __name__ == '__main__':
    unittest.main()
    
