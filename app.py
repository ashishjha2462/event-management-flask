from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from state import states_and_cities
from datetime import timedelta
from datetime import datetime
from sqlalchemy import text
from config import *
import paypalrestsdk
import os 

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER

mail = Mail(app)

db = SQLAlchemy(app)

UPLOAD_FOLDER = 'static/uploads/halls'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def send_message(message, user_id, sender):
    user = Users.query.filter((Users.id == user_id)).first()
    try:
        new_message = MessageBox(
            user_id=user_id,
            sender=sender,
            message=message,
            status='unread'
        )
        db.session.add(new_message)
        db.session.commit()
        flash('Message sent successfully!', 'success')
    except Exception as e:
        flash('Error sending message', e.message)

def send_email(to, subject, body):
    try:
        msg = Message(subject, recipients=[to])
        msg.body = body
        mail.send(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {str(e)}")

def send_cancellation_email(to, subject, body):
    try:
        msg = Message(subject, recipients=[to])
        msg.body = body
        mail.send(msg)
        print("Cancellation email sent successfully!")
    except Exception as e:
        print(f"Error sending cancellation email: {str(e)}")

def check_clash(start_datetime, end_datetime, hall_id, exclude_event_id=None):
    selected_hall = Halls.query.get(hall_id)
    if not selected_hall:
        return False   

     
    clashes = Events.query.filter(
        Events.location == selected_hall.location,
        Events.start_datetime < end_datetime,
        Events.end_datetime > start_datetime,
        Events.id != exclude_event_id   
    ).all()

    return len(clashes) > 0

def is_overlapping_appointment(date, time, appointment_id=None):
    """
    Checks if there is an overlapping appointment within 15 minutes before or after
    the given time for the same date. Excludes the current appointment being edited.
    """
    # Calculate the 15-minute range
    time_lower_bound = (datetime.combine(date, time) - timedelta(minutes=15)).time()
    time_upper_bound = (datetime.combine(date, time) + timedelta(minutes=15)).time()

    # Query for overlapping appointments
    query = Appointments.query.filter_by(date=date).filter(
        Appointments.time >= time_lower_bound,
        Appointments.time <= time_upper_bound
    )

    # Exclude the current appointment being edited
    if appointment_id:
        query = query.filter(Appointments.id != appointment_id)

    # Return True if any overlapping appointment exists
    return query.first() is not None

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) 

class Events(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.Text, nullable=False)
    event_detail = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class Halls(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)   
    type = db.Column(db.String(50), nullable=False)   
    price = db.Column(db.Float, nullable=False)   
    location = db.Column(db.String(100), nullable=False)   
    photo = db.Column(db.String(200), nullable=True)   
    capacity = db.Column(db.Integer, nullable=False)   

class Tickets(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    number_of_tickets = db.Column(db.Integer, nullable=False)

    user = db.relationship('Users', backref=db.backref('tickets', lazy=True))
    event = db.relationship('Events', backref=db.backref('tickets', lazy=True))

class Appointments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    hall_id = db.Column(db.Integer, db.ForeignKey('halls.id'), nullable=False)
    time = db.Column(db.Time, nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(26), nullable=False, default="pending-request")

    user = db.relationship('Users', backref=db.backref('appointments', lazy=True))
    event = db.relationship('Events', backref=db.backref('appointments', lazy=True))
    hall = db.relationship('Halls', backref=db.backref('appointments', lazy=True))

class MessageBox(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(10), nullable=False, default="unread")  # "read" or "unread"

    user = db.relationship('Users', backref=db.backref('messages', lazy=True))

class EventPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(10), nullable=False, default="Unpaid")
    time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('Users', backref=db.backref('eve_payements', lazy=True))
    event = db.relationship('Events', backref=db.backref('eve_payements', lazy=True))

class TicketPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(10), nullable=False, default="Unpaid")
    time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('Users', backref=db.backref('tic_payements', lazy=True))
    ticket = db.relationship('Tickets', backref=db.backref('tic_payements', lazy=True))

@app.before_request
def check_logged_in():
    if request.endpoint not in ['login', 'register', 'static'] and 'user_id' not in session:
        return redirect(url_for('login'))

@app.route('/')
def home():
    is_admin = session.get('is_admin')
    try:
         
        all_events = Events.query.order_by(Events.start_datetime.asc()).all()

        event_data = []
        for event in all_events:
            booked_tickets = Tickets.query.filter_by(event_id=event.id).with_entities(
            db.func.sum(Tickets.number_of_tickets)).scalar() or 0
            hall = Halls.query.filter_by(location=event.location).first()
            available_tickets = hall.capacity - booked_tickets if hall else 0
            event_data.append({
                "id": event.id,
                "college_name": event.college_name,
                "hall_name": hall.name,
                "event_detail": event.event_detail,
                "location": event.location,
                "start_datetime": event.start_datetime,
                "end_datetime": event.end_datetime,
                "price": event.price,
                "available_tickets": available_tickets,
                "hall_photo":hall.photo,
            })

        return render_template('home.html', events=event_data, is_admin=is_admin)
    except Exception as e:
        flash(f'Error fetching events: {str(e)}', 'danger')
        return redirect(url_for('login'))

@app.route('/about')
def about():
    is_admin = session.get('is_admin')
    return render_template('about.html', is_admin=is_admin)

@app.route('/contact')
def contact():
    is_admin = session.get('is_admin')
    return render_template('contact.html', is_admin=is_admin)

@app.route('/admin', methods=['GET'])
def admin():
    is_admin = session.get('is_admin')
    if not session.get('user_id') or not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
    try:
        # user_id = session.get('user_id')
        # message = "you loggedin as administrator"
        # send_message(message, user_id, "Admin")
        all_events = Events.query.order_by(Events.start_datetime.asc()).all()
         
        event_data = []
        for event in all_events:
            booked_tickets = Tickets.query.filter_by(event_id=event.id).with_entities(
            db.func.sum(Tickets.number_of_tickets)).scalar() or 0
            hall = Halls.query.filter_by(location=event.location).first()
            available_tickets = hall.capacity - booked_tickets if hall else 0
            event_data.append({
                "id": event.id,
                "college_name": event.college_name,
                "hall_name": hall.name,
                "event_detail": event.event_detail,
                "location": event.location,
                "start_datetime": event.start_datetime,
                "end_datetime": event.end_datetime,
                "price": event.price,
                "available_tickets": available_tickets,
                "hall_photo":hall.photo,
            })
        halls = Halls.query.all()
        return render_template('admin.html', events=event_data, halls = halls, is_admin=is_admin)
    except Exception as e:
        flash(f'Error fetching events: {str(e)}', 'danger')
        return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form_data = {key: request.form[key].strip() for key in ['username', 'name', 'password', 'confirm_password', 'phone_number', 'dob', 'email', 'city', 'state']}
        try:
             
            if form_data['password'] != form_data['confirm_password']:
                flash('Passwords do not match!', 'danger')
                return redirect(url_for('register'))

             
            dob_date = datetime.strptime(form_data['dob'], '%Y-%m-%d')
            if (datetime.now() - dob_date).days // 365 < 18:
                flash('You must be at least 18 years old to register!', 'danger')
                return redirect(url_for('register'))

             
            if Users.query.filter((Users.username == form_data['username']) | (Users.email == form_data['email'])).first():
                flash('Username or email is already registered!', 'danger')
                return redirect(url_for('register'))

             
            new_user = Users(
                username=form_data['username'], 
                name=form_data['name'], 
                password=generate_password_hash(form_data['password']),
                phone_number=form_data['phone_number'], 
                dob=dob_date, 
                email=form_data['email'], 
                city=form_data['city'], 
                state=form_data['state']
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            app.logger.error(f"Error during registration: {e}")
            return redirect(url_for('register'))

    return render_template('register.html', today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

         
        user = Users.query.filter_by(email=email).first()

         
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            return redirect(url_for('admin') if user.is_admin else url_for('home'))
        else:
            flash('Invalid email or password!', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/create-event', methods=['GET', 'POST'])
def create_event():
    if not session.get('user_id'):
        flash('Please log in to create an event!', 'danger')
        return redirect(url_for('login'))

    is_admin = session.get('is_admin')
    halls = Halls.query.all()
    user_id = session.get('user_id')
    user = Users.query.filter((Users.id == user_id)).first()

    if request.method == 'POST':
        try:
            hall_id = int(request.form['hall_id'])
            selected_hall = Halls.query.get(hall_id)

             
            if not selected_hall:
                flash('Selected hall does not exist.', 'danger')
                return redirect(url_for('create_event'))

             
            start_datetime = datetime.strptime(request.form['start_datetime'], '%Y-%m-%dT%H:%M')
            end_datetime = datetime.strptime(request.form['end_datetime'], '%Y-%m-%dT%H:%M')
            if start_datetime >= end_datetime:
                flash('Start time must be before end time.', 'danger')
                return redirect(url_for('create_event'))
            
            if check_clash(start_datetime, end_datetime, hall_id):
                flash('Error: Event times conflict with an existing event!', 'danger')
                return redirect(url_for('create_event'))

             
            form_data = {
                'college_name': request.form['college_name'].strip(),
                'address': selected_hall.location,
                'event_detail': request.form['event_detail'].strip(),
                'location': selected_hall.location,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'description': request.form['description'].strip(),
                'event_type': selected_hall.type,
                'price': selected_hall.price / 20,
                'created_by': session['user_id']
            }

             
            new_event = Events(**form_data)
            db.session.add(new_event)
            db.session.commit()

            flash('Event created successfully!', 'success')

            subject = f"Event Creation Confirmation for {new_event.event_detail}"
            body = f"""
            Dear {user.name},

            Thank you for Creating event for {new_event.event_detail}.
            Here are your Event details:

            Event: {new_event.event_detail}
            Location: {new_event.location}
            Start Time: {new_event.start_datetime}
            End Time: {new_event.end_datetime}

            We look forward to seeing you at the event!

            Best regards,
            Event Management Team
            """
            send_email(user.email, subject, body)

            return redirect(url_for('events'))

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('create_event.html', halls=halls, is_admin=is_admin)

@app.route('/events')
def events():
    is_admin = session.get('is_admin')
    try:
         
        all_events = Events.query.order_by(Events.start_datetime.asc()).all()

         
        event_data = []
        for event in all_events:
            booked_tickets = Tickets.query.filter_by(event_id=event.id).with_entities(
            db.func.sum(Tickets.number_of_tickets)).scalar() or 0
            hall = Halls.query.filter_by(location=event.location).first()
            available_tickets = hall.capacity - booked_tickets if hall else 0
            event_data.append({
                "id": event.id,
                "college_name": event.college_name,
                "hall_name": hall.name,
                "event_detail": event.event_detail,
                "location": event.location,
                "start_datetime": event.start_datetime,
                "end_datetime": event.end_datetime,
                "price": event.price,
                "available_tickets": available_tickets,
            })

        return render_template('events.html', events=event_data, is_admin=is_admin)
    except Exception as e:
        flash(f'Error fetching events: {str(e)}', 'danger')
        return redirect(url_for('home'))
    
@app.route('/admin/users')
def manage_users():
    users = Users.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = Users.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.name = request.form['name']
        user.phone_number = request.form['phone_number']
        user.dob = datetime.strptime(request.form['dob'], '%Y-%m-%d')
        user.email = request.form['email']
        user.city = request.form['city']
        user.state = request.form['state']
        user.is_admin = 'is_admin' in request.form

        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('manage_users'))

    return render_template('edit_user.html', user=user)

@app.route('/admin/users/delete/<int:user_id>', methods=['GET', 'POST'])
def delete_user(user_id):
    user = Users.query.get_or_404(user_id)

    if request.method == 'POST':
        # Delete dependencies
        Tickets.query.filter_by(user_id=user.id).delete()
        Events.query.filter_by(created_by=user.id).delete()

        db.session.delete(user)
        db.session.commit()

        flash('User and related data deleted successfully!', 'success')
        return redirect(url_for('manage_users'))

    return render_template('delete_user.html', user=user)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to view your profile!', 'danger')
        return redirect(url_for('login'))

    user = Users.query.get(user_id)

    # Update user details
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.phone_number = request.form.get('phone_number')
        user.dob = request.form.get('dob')
        user.city = request.form.get('city')
        user.state = request.form.get('state')
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    events = Events.query.filter(Events.created_by == user_id).all()
    tickets = Tickets.query.filter(Tickets.user_id == user_id).all()
    return render_template('profile.html', user=user, events=events, tickets=tickets)

@app.route('/admin/halls', methods=['GET', 'POST'])
def manage_halls():
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    is_admin = session.get('is_admin')
    if request.method == 'POST':
        try:
             
            hall_data = {
                'name': request.form['name'].strip(),
                'type': request.form['type'].strip(),
                'price': float(request.form['price']),
                'location': request.form['name'].strip() + ", " + request.form['location'].strip(),
                'capacity': int(request.form['capacity']),
            }

            photo = request.files['photo']
            if photo:
                filename = secure_filename(photo.filename)
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)
                hall_data['photo'] = photo_path

             
            new_hall = Halls(**hall_data)
            db.session.add(new_hall)
            db.session.commit()

            flash('Hall added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding hall: {e}', 'danger')

    halls = Halls.query.all()
    return render_template('manage_halls.html', halls=halls, is_admin=is_admin)

@app.route('/admin/halls/edit/<int:hall_id>', methods=['GET', 'POST'])
def edit_hall(hall_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    hall = Halls.query.get_or_404(hall_id)
    events = Events.query.filter_by(location=hall.location).all()

    if request.method == 'POST':
        try:
            hall.name = request.form['name'].strip()
            hall.type = request.form['type'].strip()
            hall.price = float(request.form['price'])
            hall.location = request.form['location'].strip()
            hall.capacity = int(request.form['capacity'])
            for event in events:
                event.location = hall.location
                event.address = hall.location
                event.type = hall.type
                event.price = hall.price / 20
                tickets = Tickets.query.filter_by(event_id=event.id)
                for ticket in tickets:
                    ticket.event_id = event.id
             
            photo = request.files['photo']
            if photo:
                filename = secure_filename(photo.filename)
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)
                hall.photo = photo_path

            db.session.commit()
            flash('Hall updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating hall: {e}', 'danger')

        return redirect(url_for('manage_halls'))

    return render_template('edit_hall.html', hall=hall)

@app.route('/admin/halls/delete/<int:hall_id>', methods=['POST'])
def delete_hall(hall_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    hall = Halls.query.get_or_404(hall_id)
    try:
         
        events = Events.query.filter_by(location=hall.location).all()
        for event in events:
            Tickets.query.filter_by(event_id=event.id).delete()
            db.session.delete(event)

        db.session.delete(hall)
        db.session.commit()

        flash('Hall and related data deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting hall: {e}', 'danger')

    return redirect(url_for('manage_halls'))

@app.route('/admin/events', methods=['GET', 'POST'])
def manage_events():
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    halls = Halls.query.all()   
    events = Events.query.all()   

    if request.method == 'POST':
        try:
            hall_id = int(request.form['hall_id'])
            selected_hall = Halls.query.get(hall_id)

             
            if not selected_hall:
                flash('Selected hall does not exist.', 'danger')
                return redirect(url_for('manage_events'))
            
             
            start_datetime = datetime.strptime(request.form['start_datetime'], '%Y-%m-%dT%H:%M')
            end_datetime = datetime.strptime(request.form['end_datetime'], '%Y-%m-%dT%H:%M')
            if start_datetime >= end_datetime:
                flash('Start time must be before end time.', 'danger')
                return redirect(url_for('manage_events'))

             
            event_data = {
                'college_name': request.form['college_name'].strip(),
                'address': selected_hall.location,
                'event_detail': request.form['event_detail'].strip(),
                'location': selected_hall.location,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'description': request.form['description'].strip(),
                'event_type': selected_hall.type,
                'price': selected_hall.price,
                'created_by': session['user_id']
            }

            if check_clash(start_datetime, end_datetime, hall_id):
                flash('Error: Event times conflict with an existing event!', 'danger')
                return redirect(url_for('manage_events'))

             
            new_event = Events(**event_data)
            db.session.add(new_event)
            db.session.commit()

            flash('Event added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding event: {e}', 'danger')
    events = Events.query.all()
    return render_template('manage_events.html', events=events, halls=halls)

@app.route('/admin/events/edit/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    event = Events.query.get_or_404(event_id)
    halls = Halls.query.all()
    tickets = Tickets.query.filter_by(event_id=event.id)

    if request.method == 'POST':
        try:
            hall_id = int(request.form['hall_id'])
            selected_hall = Halls.query.get(hall_id)
            event.college_name = request.form['college_name'].strip()
            event.event_detail = request.form['event_detail'].strip()
            event.location = selected_hall.location
            event.price = selected_hall.price / 20
            event.address = selected_hall.location
            event.event_type = selected_hall.type
            event.start_datetime = datetime.strptime(request.form['start_datetime'], '%Y-%m-%dT%H:%M')
            event.end_datetime = datetime.strptime(request.form['end_datetime'], '%Y-%m-%dT%H:%M')
            event.description = request.form['description'].strip()

            if check_clash(event.start_datetime, event.end_datetime, hall_id, exclude_event_id=event.id):
                flash('Error: Event times conflict with an existing event!', 'danger')
                return redirect(url_for('manage_events'))
            
            for ticket in tickets:
                ticket.event_id = event.id

            db.session.commit()
            flash('Event updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating event: {e}', 'danger')

        return redirect(url_for('manage_events'))

    return render_template('edit_event.html', event=event, halls=halls)

@app.route('/admin/events/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    event = Events.query.get_or_404(event_id)
    try:
        db.session.delete(event)
        db.session.commit()
        flash('Event deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting event: {e}', 'danger')

    return redirect(url_for('manage_events'))

@app.route('/admin/tickets', methods=['GET'])
def manage_tickets():
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
    
    tickets = Tickets.query.all()
    return render_template('manage_tickets.html', tickets=tickets)

@app.route('/admin/tickets/edit/<int:ticket_id>', methods=['POST'])
def edit_ticket(ticket_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
    
    ticket = Tickets.query.get_or_404(ticket_id)
    try:
        new_ticket_count = int(request.form.get('new_ticket_count'))
        if new_ticket_count < 1 or new_ticket_count > ticket.number_of_tickets:
            flash('Invalid ticket count!', 'danger')
            return redirect(url_for('manage_tickets'))

        ticket.number_of_tickets = new_ticket_count
        db.session.commit()

        flash('Ticket count updated successfully!', 'success')
        return redirect(url_for('manage_tickets'))
    except Exception as e:
        flash(f'Error updating ticket: {str(e)}', 'danger')
        return redirect(url_for('manage_tickets'))

@app.route('/admin/tickets/cancel_booking/<int:ticket_id>', methods=['POST'])
def cancel_booking(ticket_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
    
    ticket = Tickets.query.get_or_404(ticket_id)
    try:
        user = db.session.get(Users, ticket.user_id)
        event = db.session.get(Events, ticket.event_id)

        subject = f"Ticket Cancellation for {event.event_detail}"
        body = f"""
        Dear {user.name},

        Cancellation of ticket for {event.event_detail} is confirmed.
        Here are your cancelled booking details:

        Event: {event.event_detail}
        Location: {event.location}
        Start Time: {event.start_datetime}
        End Time: {event.end_datetime}

        Please contact us if you have any questions or concerns.

        Best regards,
        Event Management Team
        """
        send_cancellation_email(user.email, subject, body)
        
         
        db.session.delete(ticket)
        db.session.commit()
        flash('Ticket cancellation successful!', 'success')
        return redirect(url_for('manage_tickets'))
    except Exception as e:
        flash(f'Error cancelling ticket: {e}', 'danger')
        return redirect(url_for('manage_tickets'))

@app.route('/book-ticket/<int:event_id>', methods=['GET', 'POST'])
def book_ticket(event_id):
    if not session.get('user_id'):
        flash('Please log in to book tickets!', 'danger')
        return redirect(url_for('login'))

    is_admin = session.get('is_admin')
    try:
        event = Events.query.get_or_404(event_id)
        user_id = session['user_id']

        booked_tickets = Tickets.query.filter_by(event_id=event.id).with_entities(
            db.func.sum(Tickets.number_of_tickets)).scalar() or 0
        hall = Halls.query.filter_by(location=event.location).first()
        available_tickets = hall.capacity - booked_tickets

        if request.method == 'POST':
            number_of_tickets = int(request.form.get('number_of_tickets', 0))

            if number_of_tickets <= 0:
                flash('Invalid number of tickets!', 'danger')
                return redirect(url_for('book_ticket', event_id=event_id))

            if number_of_tickets > available_tickets:
                flash(f'Only {available_tickets} tickets are available!', 'danger')
                return redirect(url_for('book_ticket', event_id=event_id))

            existing_ticket = Tickets.query.filter_by(user_id=user_id, event_id=event_id).first()
            if existing_ticket:
                flash('You have already booked tickets for this event!', 'warning')
                return redirect(url_for('events'))

            new_ticket = Tickets(user_id=user_id, event_id=event_id, number_of_tickets=number_of_tickets)
            db.session.add(new_ticket)
            db.session.commit()

            user = db.session.get(Users, user_id)

            subject = f"Ticket Confirmation for {event.event_detail}"
            body = f"""
            Dear {user.name},

            Thank you for booking tickets for {event.event_detail}.
            Here are your booking details:

            Event: {event.event_detail}
            Location: {event.location}
            Start Time: {event.start_datetime}
            End Time: {event.end_datetime}
            Tickets Booked: {number_of_tickets}

            We look forward to seeing you at the event!

            Best regards,
            Event Management Team
            """
            send_email(user.email, subject, body)

            flash('Tickets booked successfully!', 'success')
            return redirect(url_for('events'))

        return render_template('book_ticket.html', event=event, is_admin=is_admin, available_tickets=available_tickets)
    except Exception as e:
        flash(f'Error booking tickets: {str(e)}', 'danger')
        return redirect(url_for('events'))

@app.route('/cancel_booking_user/<int:ticket_id>', methods=['POST'])
def cancel_booking_user(ticket_id):
    if not session.get('user_id'):
        flash('Please log in to cancel bookings!', 'danger')
        return redirect(url_for('login'))
    ticket = Tickets.query.get_or_404(ticket_id)
    try:
         
        user = db.session.get(Users, ticket.user_id)
        event = db.session.get(Events, ticket.event_id)
         
        subject = f"Ticket Cancellation for {event.event_detail}"
        body = f"""
        Dear {user.name},

        Cancellation of ticket for {event.event_detail} is confirmed.
        Here are your cancelled booking details:

        Event: {event.event_detail}
        Location: {event.location}
        Start Time: {event.start_datetime}
        End Time: {event.end_datetime}

        Please contact us if you have any questions or concerns.

        Best regards,
        Event Management Team
        """
        send_cancellation_email(user.email, subject, body)
        
         
        db.session.delete(ticket)
        db.session.commit()
        flash('Ticket cancellation successful!', 'success')
        return redirect(url_for('my_bookings'))
    except Exception as e:
        flash(f'Error cancelling ticket: {e}', 'danger')
        return redirect(url_for('my_bookings'))

@app.route('/my-bookings')
def my_bookings():
    if not session.get('user_id'):
        flash('Please log in to view your bookings!', 'danger')
        return redirect(url_for('login'))
    is_admin = session.get('is_admin')
    try:
        user_id = session['user_id']
        tickets = Tickets.query.filter_by(user_id=user_id).all()

        return render_template('my_bookings.html', tickets=tickets, is_admin=is_admin)
    except Exception as e:
        flash(f'Error fetching bookings: {str(e)}', 'danger')
        return redirect(url_for('home'))
    
@app.route('/make-appointment', methods=['GET', 'POST'])
def make_appointment():
    if not session.get('user_id'):
        flash('Please log in to make an appointment!', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    events = Events.query.filter_by(created_by=user_id).all()
    halls = Halls.query.all()
    user_appointments = Appointments.query.filter_by(user_id=user_id).all()
    user = Users.query.filter((Users.id == user_id)).first()

    if request.method == 'POST':
        try:
            # Extract data from the form
            event_id = int(request.form['event_id'])
            hall_id = int(request.form['hall_id'])
            date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            time = datetime.strptime(request.form['time'], '%H:%M').time()

            # Check for overlapping appointments globally
            if is_overlapping_appointment(date, time):
                flash('There is already an appointment within 15 minutes of the selected time.', 'danger')
                return redirect(url_for('make_appointment'))

            # Save the appointment
            appointment_data = {
                'user_id': user_id,
                'event_id': event_id,
                'hall_id': hall_id,
                'date': date,
                'time': time,
                'status': 'request-pending'
            }

            new_appointment = Appointments(**appointment_data)
            db.session.add(new_appointment)
            db.session.commit()

            flash('Appointment request sent successfully!', 'success')
        except Exception as e:
            flash(f'Error creating appointment: {str(e)}', 'danger')

    return render_template('appointments.html', appointments=user_appointments, events=events, halls=halls)

@app.route('/admin/appointments', methods=['GET', 'POST'])
def manage_appointments():
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    appointments = Appointments.query.order_by(Appointments.date.desc(), Appointments.time.desc()).all()

    if request.method == 'POST':
        try:
            # Extract data from the form
            user_id = int(request.form['user_id'])
            event_id = int(request.form['event_id'])
            hall_id = int(request.form['hall_id'])
            date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            time = datetime.strptime(request.form['time'], '%H:%M').time()

            # Check for overlapping appointments globally
            if is_overlapping_appointment(date, time):
                flash('There is already an appointment within 15 minutes of the selected time.', 'danger')
                return redirect(url_for('manage_appointments'))

            # Save the appointment
            appointment_data = {
                'user_id': user_id,
                'event_id': event_id,
                'hall_id': hall_id,
                'date': date,
                'time': time,
                'status': 'request-pending'
            }

            new_appointment = Appointments(**appointment_data)
            db.session.add(new_appointment)
            db.session.commit()

            flash('Appointment added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding appointment: {str(e)}', 'danger')

    return render_template('manage_appointments.html', appointments=appointments)

@app.route('/admin/appointments/complete/<int:appointment_id>', methods=['POST'])
def complete_appointment(appointment_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    appointment = Appointments.query.get_or_404(appointment_id)
    user = Users.query.get(appointment.user_id)
    event = Events.query.get(appointment.event_id)
    try:
        appointment.status = 'request-approved'
        db.session.commit()
        flash('Appointment marked as approved!', 'success')
        subject = f"Appointment confirmed for {event.event_detail}"
        body = f"""
        Dear {user.name},

        Your Appointment request for {event.event_detail} has been approved.
        Here are your Appointment details:

        Event: {event.event_detail}
        Timing: {appointment.time}
        Date: {appointment.date}

        We look forward to seeing you for you appointment!
        Best regards,

        Event Management Team
        """
        send_email(user.email, subject, body)
    except Exception as e:
        flash(f'Error completing appointment: {str(e)}', 'danger')

    return redirect(url_for('manage_appointments'))

@app.route('/admin/appointments/edit/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    appointment = Appointments.query.get_or_404(appointment_id)
    events = Events.query.all()
    halls = Halls.query.all()
    users = Users.query.all()

    if request.method == 'POST':
        try:
            # Extract data from the form
            user_id = int(request.form['user_id'])
            event_id = int(request.form['event_id'])
            hall_id = int(request.form['hall_id'])
            date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            time = datetime.strptime(request.form['time'], '%H:%M').time()

            # Check for overlapping appointments globally
            if is_overlapping_appointment(date, time, appointment_id):
                flash('There is already an appointment within 15 minutes of the selected time.', 'danger')
                return redirect(url_for('edit_appointment', appointment_id=appointment_id))

            # Update appointment data
            appointment.user_id = user_id
            appointment.event_id = event_id
            appointment.hall_id = hall_id
            appointment.date = date
            appointment.time = time
            appointment.status = 'request-pending'
            db.session.commit()

            flash('Appointment updated successfully!', 'success')
            return redirect(url_for('manage_appointments'))
        except Exception as e:
            flash(f'Error updating appointment: {str(e)}', 'danger')

    return render_template('edit_appointment.html', appointment=appointment, events=events, halls=halls, users = users)

@app.route('/admin/appointments/delete/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    appointment = Appointments.query.get_or_404(appointment_id)
    try:
        db.session.delete(appointment)
        db.session.commit()
        flash('Appointment deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting appointment: {str(e)}', 'danger')

    return redirect(url_for('manage_appointments'))

@app.route('/messages', methods=['GET', 'POST'])
def messages():
    if not session.get('user_id'):
        flash('Please log in to view messages!', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = Users.query.filter((Users.id == user_id)).first()
    if request.method == 'POST':
        try:
            new_message = MessageBox(
                user_id=user_id,
                sender=user.username,
                message=request.form['message'].strip(),
                status='unread'
            )
            db.session.add(new_message)
            db.session.commit()
            flash('Message sent successfully!', 'success')
        except Exception as e:
            flash(f'Error sending message: {str(e)}', 'danger')

    if session.get('is_admin'):
        user_messages = MessageBox.query.order_by(MessageBox.id.desc()).all()
    else:
        user_messages = MessageBox.query.filter_by(user_id=user_id).order_by(MessageBox.id.desc()).all()
    return render_template('messages.html', messages=user_messages, c_user=user)

@app.route('/messages/mark_read/<int:message_id>', methods=['POST'])
def mark_message_read_user(message_id):
    if not session.get('user_id'):
        flash('Please log in to view messages!', 'danger')
        return redirect(url_for('login'))

    message = MessageBox.query.get_or_404(message_id)
    try:
        message.status = 'read'
        db.session.commit()
        flash('Message marked as read!', 'success')
    except Exception as e:
        flash(f'Error marking message as read: {str(e)}', 'danger')

    return redirect(url_for('messages'))

@app.route('/admin/messages', methods=['GET', 'POST'])
def admin_messages():
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = Users.query.filter((Users.id == user_id)).first()
    users = Users.query.all()
    if request.method == 'POST':
        try:
            new_message = MessageBox(
                user_id=int(request.form['user_id']),
                sender=user.username,
                message=request.form['message'].strip(),
                status='unread'
            )
            db.session.add(new_message)
            db.session.commit()
            flash('Reply sent successfully!', 'success')
        except Exception as e:
            flash(f'Error sending: {str(e)}', 'danger')

    c_messages = MessageBox.query.order_by(MessageBox.id.desc()).all()
    for msg in c_messages:
        print(msg)
    return render_template('admin_messages.html', messages=c_messages, users = users, c_user=user)

@app.route('/admin/messages/mark_read/<int:message_id>', methods=['POST'])
def mark_message_read(message_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    message = MessageBox.query.get_or_404(message_id)
    try:
        message.status = 'read'
        db.session.commit()
        flash('Message marked as read!', 'success')
    except Exception as e:
        flash(f'Error marking message as read: {str(e)}', 'danger')

    return redirect(url_for('admin_messages'))
@app.route('/admin/messages/delete_message/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    if not session.get('is_admin'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    message = MessageBox.query.get_or_404(message_id)
    try:
        db.session.delete(message)
        db.session.commit()
        flash('Message successfully deleted!', 'success')
    except Exception as e:
        flash(f'Error deleting message: {str(e)}', 'danger')

    return redirect(url_for('admin_messages'))

@app.route('/messages/delete_message_user/<int:message_id>', methods=['POST'])
def delete_message_user(message_id):
    if not session.get('user_id'):
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    message = MessageBox.query.get_or_404(message_id)
    try:
        db.session.delete(message)
        db.session.commit()
        flash('Message successfully deleted!', 'success')
    except Exception as e:
        flash(f'Error deleting message: {str(e)}', 'danger')

    return redirect(url_for('admin_messages'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/test_connection')
def test_connection():
    try:
         
        db.session.execute(text('SELECT * FROM users'))
        return "Database connected successfully!"
    except Exception as e:
        return f"Database connection failed: {str(e)}"
    
@app.route("/states-cities")
def states_cities():
    return jsonify(states_and_cities)

if __name__ == '__main__':
    app.run(debug=True)