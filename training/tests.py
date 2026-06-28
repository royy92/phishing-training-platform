from django.test import TestCase
from django.urls import reverse

# Create your tests here.
class HomePageTests(TestCase):
    def test_home_page_returns_200(self):
        # Arrange
        url = reverse("training:home")

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, 200)
