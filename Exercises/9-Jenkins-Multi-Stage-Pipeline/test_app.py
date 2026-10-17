import unittest
from app import app


class TestApp(unittest.TestCase):
    def test_home(self):
        client = app.test_client()
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Hello, Jenkins Multi-Stage Pipeline!', response.data)
        print(response.data.decode())


if __name__ == '__main__':
    unittest.main()
