**Event Garden**

Event Garden is a web-based event management system built using Flask and SQLAlchemy with MySQL integration. This system allows users to create, manage, and book events with ease while providing robust administrative controls.

Features

User Features

User Registration:

Fields: username, password, confirm password, mobile number, date of birth, email ID, city, and state.

Built-in validation for all fields.

Secure Login:

Login using email and password.

Pages:

Home

About

Events

Register Event

Gallery

Contact

Admin Features

Admin Page:

Accessible only to admin users.

Manage all user functionalities.

Event Management:

Create, update, delete, and view events.

Manage event locations, prices, and maximum capacities.

Hall Management:

CRUD operations for halls, including type (seminar, party, gathering, lecture, etc.), price, location, photo, and capacity.

User Overview:

View lists of event creators and ticket bookers in a tabular format.

Event Management

Event Details:

Fields: college name, address, event details, location, start date/time, end date/time, description, type, and price.

Prevents overlapping events at the same location and time.

Hall Selection:

Automatically populates address, event type, and price based on selected hall.

Ticket Booking

Users can create and register for events by booking tickets.

Installation

Prerequisites

Python 3.x

MySQL Server

Virtual environment (optional but recommended)

Steps

Clone the repository:

git clone <repository-url>

Navigate to the project directory:

cd event-garden

Set up a virtual environment:

python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Configure the database:

Create a MySQL database.

Update the config.py file with your database credentials.

Run database migrations:

flask db upgrade

Start the development server:

flask run

Access the application in your browser:

Development: http://127.0.0.1:5000

Project Structure

project/
|-- static/         # Static files (CSS, JavaScript, images)
|-- templates/      # HTML templates
|-- app.py          # Application entry point
|-- models.py       # Database models
|-- routes.py       # Application routes
|-- config.py       # Configuration file
|-- requirements.txt # Dependencies

Contributing

Contributions are welcome! Please fork the repository and create a pull request for any features or bug fixes you implement.

License

This project is licensed under the MIT License. See the LICENSE file for more details.

Contact

For any questions or feedback, feel free to contact:

Email: [ashish.jha.2462@gmail.com]

GitHub: [[your-github-profile-url](https://github.com/ashishjha2462/)]

