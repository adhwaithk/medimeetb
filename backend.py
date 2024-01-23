from flask_socketio import SocketIO
import socketio
from flask import Flask, request, jsonify, session, render_template
from flask_session import Session
import mysql.connector
from flask_cors import CORS
from flask import jsonify
from datetime import datetime
import stripe
from flask_socketio import SocketIO, emit

app = Flask(__name__)

socketio = SocketIO(app)
CORS(app)
app.secret_key = 'loginsecret'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'booking',
}
mysql = mysql.connector.connect(**db_config)

# Set your secret key
stripe.api_key = 'sk_test_51ODnq2SFyl6IAnvdX6BH9RfBWyk1TlHYdm9zkCeAfIaXrV8cSigm2FmpbzSQfzwLShDRAFvNmGYGYqB7zg5vNBsd00ZlYT6cXE'
stripe.api_version = '2020-03-02'  # Use the latest version available


# Route for patient registration
@app.route('/patient/register', methods=['POST'])
def register_patient():
    try:
        data = request.get_json()
        print("Received Data:", data)  # Log received data for debugging

        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        # Check received data
        if not (name and email and password):
            return jsonify({"error": "Incomplete data received"}), 400

        cursor = mysql.cursor()
        cursor.execute('INSERT INTO patients (name, email, password) VALUES (%s, %s, %s)', (name, email, password))
        mysql.commit()
        cursor.close()

        return jsonify({"message": "Thank you for signing up! You can now login."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route for patient or doctor login
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        user_type = data.get('user_type')  # 'patient' or 'doctor'

        cursor = mysql.cursor()

        if user_type == 'patient':
            cursor.execute('SELECT patient_id, name, email, password FROM patients WHERE email = %s', (email,))
        elif user_type == 'doctor':
            cursor.execute('SELECT id, name, email, password FROM doctors WHERE email = %s', (email,))
        else:
            return jsonify({"error": "Invalid user type"}), 400

        user = cursor.fetchone()
        cursor.close()

        if user and user[3] == password:
            # Store user ID and type in the session to mark the user as logged in
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_type'] = user_type

            # Redirect to the main homepage based on user type
            if user_type == 'patient':
                return jsonify({"message": "Logged in successfully!", "user_name": user[1], "user_type":'patient'}), 200
            elif user_type == 'doctor':
                return jsonify({"message": "Logged in successfully!", "user_name": user[1],"user_type":'doctor'}), 200
        else:
            return jsonify({"error": "Invalid email or password"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route for patient logout (dummy example)
@app.route('/logout', methods=['POST'])
def logout_patient():
    try:
        # Check if the patient is logged in
        if 'patient_id' in session:
            session.pop('patient_id', None)
            session.pop('patient_name', None)

            return jsonify({"message": "Logged out successfully"}), 200
        else:
            return jsonify({"message": "Patient is not logged in"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


from datetime import datetime

@app.route('/patient/appointment', methods=['POST'])
def create_appointment():
    try:
        data = request.get_json()
        print("Received Data:", data)  # Log received data for debugging

        patient_name = data.get('patient_name')
        age = data.get('age')
        gender = data.get('gender')
        mobile = data.get('mobile')
        email = data.get('email')
        address = data.get('address')
        appointment_time_str = data.get('appointment_time')
        doctor_name = data.get('doctor_name')
        doctor_id = data.get('doctor_id')
        reason = data.get('reason')
        symptoms = data.get('symptoms')
        ongoing_medications = data.get('ongoing_medications')
        allergies = data.get('allergies')
        height = data.get('height')
        weight = data.get('weight')

        # Parse the appointment_time string with the correct format
        appointment_time = datetime.strptime(appointment_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')

        cursor = mysql.cursor()
        cursor.execute(
            '''INSERT INTO appoinments (
                patient_name, age, gender, mobile, email, address,
                appointment_time, doctor_name, doctor_id, reason, symptoms,
                ongoing_medications, allergies, height, weight
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (patient_name, age, gender, mobile, email, address,
             appointment_time.strftime('%Y-%m-%d %H:%M:%S'), doctor_name, doctor_id,
             reason, symptoms, ongoing_medications, allergies, height, weight)
        )
        mysql.commit()
        cursor.close()

        return jsonify({"message": "Appointment created successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/doctors', methods=['GET'])
def get_doctors_by_category():
    try:
        specialized_category = request.args.get('specialized_category')

        if not specialized_category:
            return jsonify({"error": "Specialized category not provided"}), 400

        cursor = mysql.cursor()
        cursor.execute('SELECT * FROM doctor WHERE specialized_category = %s', (specialized_category,))
        doctors = cursor.fetchall()
        cursor.close()

        if not doctors:
            return jsonify({"message": "No doctors found for the specified category"}), 404

        # Convert the result to a list of dictionaries
        doctors_list = []
        for doctor in doctors:
            doctor_dict = {
                "doctor_id": doctor[0],
                "specialized_category": doctor[1],
                "name": doctor[2],
                "rating": float(doctor[3]),
                "price": float(doctor[4]),  # Convert to float if needed
            }
            doctors_list.append(doctor_dict)

        return jsonify({"doctors": doctors_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/all-doctors', methods=['GET'])
def get_doctors():
    try:
        cursor = mysql.cursor(dictionary=True)
        cursor.execute('SELECT * FROM doctor')
        doctors = cursor.fetchall()
        cursor.close()

        return jsonify(doctors), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/video')
def video():
    return jsonify({"message": "Video route accessed successfully"})


@socketio.on('offer')
def handle_offer(offer, room):
    # Broadcast both video and audio tracks
    socketio.emit('offer', offer, room=room)

@socketio.on('answer')
def handle_answer(answer, room):
    # Broadcast both video and audio tracks
    socketio.emit('answer', answer, room=room)

@socketio.on('ice_candidate')
def handle_ice_candidate(candidate, room):
    # Broadcast both video and audio tracks
    socketio.emit('ice_candidate', candidate, room=room)


@app.route('/doctor/appointments', methods=['GET'])
def get_doctor_appointments():
    try:
        doctor_name = request.args.get('doctor_name')

        if not doctor_name:
            return jsonify({"error": "Doctor name is required"}), 400

        cursor = mysql.cursor()
        cursor.execute(
            '''SELECT 
                appointment_id, patient_name, age, gender, mobile, email, address,
                appointment_time, doctor_name, doctor_id, reason, symptoms,
                ongoing_medications, allergies, height, weight
            FROM appoinments
            WHERE doctor_name = %s''',
            (doctor_name,))
        appointments = cursor.fetchall()
        cursor.close()

        # Convert the result to a list of dictionaries for JSON response
        appointments_list = [
            {
                "appointment_id": appointment[0],
                "patient_name": appointment[1],
                "age": appointment[2],
                "gender": appointment[3],
                "mobile": appointment[4],
                "email": appointment[5],
                "address": appointment[6],
                "appointment_time": appointment[7].isoformat(),
                "doctor_name": appointment[8],
                "doctor_id": appointment[9],
                "reason": appointment[10],
                "symptoms": appointment[11],
                "ongoing_medications": appointment[12],
                "allergies": appointment[13],
                "height": appointment[14],
                "weight": appointment[15]
            } for appointment in appointments]

        if not appointments_list:
            return jsonify({"message": "No appointments found for this doctor"}), 200

        return jsonify({"appointments": appointments_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
            
@app.route('/complete-appointment', methods=['POST'])
def complete_appointment():
    try:
        data = request.get_json()

        if not data or 'appointment_id' not in data:
            return jsonify({"error": "Appointment ID is required in the request body"}), 400

        appointment_id = data['appointment_id']

        cursor = mysql.cursor(dictionary=True)
        cursor.execute(
            'SELECT * FROM appoinments WHERE appointment_id = %s',
            (appointment_id,))
        appointment = cursor.fetchone()

        if not appointment:
            return jsonify({"error": "Appointment not found"}), 404
        cursor.execute(
            'DELETE FROM appoinments WHERE appointment_id = %s',
            (appointment_id,))
        mysql.commit()

        insert_query = '''
            INSERT INTO completed_consultations (
                patient_name, age, gender, mobile, email, address, appointment_time, doctor_name,
                reason_for_consultation, symptoms, ongoing_medications,
                allergies, height, weight
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        cursor.execute(
            insert_query,
            (
                appointment['patient_name'],
                appointment['age'],
                appointment['gender'],
                appointment['mobile'],
                appointment['email'],
                appointment['address'],
                appointment['appointment_time'],
                appointment['doctor_name'],
                appointment['reason'],
                appointment['symptoms'],
                appointment['ongoing_medications'],
                appointment['allergies'],
                appointment['height'],
                appointment['weight']
            )
        )
        mysql.commit()
        cursor.close()

        return jsonify({"message": "Appointment consulted and moved to completed_consultations"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/view-completed-consultations', methods=['GET'])
def view_completed_consultations():
    try:
        doctor_name = request.args.get('doctor_name')

        if not doctor_name:
            return jsonify({"error": "Doctor name is required"}), 400

        cursor = mysql.cursor(dictionary=True)
        cursor.execute(
            '''SELECT 
                patient_name, age, gender, mobile, email, address,
                appointment_time, doctor_name, reason_for_consultation, symptoms,
                ongoing_medications, allergies, height, weight
            FROM completed_consultations
            WHERE doctor_name = %s''',
            (doctor_name,))
        completed_consultations = cursor.fetchall()
        cursor.close()
        consultations_list = [
            {
                "patient_name": consultation['patient_name'],
                "age": consultation['age'],
                "gender": consultation['gender'],
                "mobile": consultation['mobile'],
                "email": consultation['email'],
                "address": consultation['address'],
                "appointment_time": consultation['appointment_time'].isoformat(),
                "doctor_name": consultation['doctor_name'],
                "reason_for_consultation": consultation['reason_for_consultation'],
                "symptoms": consultation['symptoms'],
                "ongoing_medications": consultation['ongoing_medications'],
                "allergies": consultation['allergies'],
                "height": consultation['height'],
                "weight": consultation['weight']
            } for consultation in completed_consultations]

        if not consultations_list:
            return jsonify({"message": "No completed consultations found for this doctor"}), 200

        return jsonify({"completed_consultations": consultations_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False)