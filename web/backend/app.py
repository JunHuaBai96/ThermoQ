from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///thermoq.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Element(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(2), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    atomic_number = db.Column(db.Integer, nullable=False)
    atomic_mass = db.Column(db.Float, nullable=False)

class Composition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    element_id = db.Column(db.Integer, db.ForeignKey('element.id'), nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(10), nullable=False)  # 'wt%' or 'at%'
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# Routes
@app.route('/api/elements', methods=['GET'])
def get_elements():
    elements = Element.query.all()
    return jsonify([{
        'id': e.id,
        'symbol': e.symbol,
        'name': e.name,
        'atomic_number': e.atomic_number,
        'atomic_mass': e.atomic_mass
    } for e in elements])

@app.route('/api/compositions', methods=['POST'])
def create_composition():
    data = request.json
    try:
        composition = Composition(
            element_id=data['element_id'],
            percentage=data['percentage'],
            unit=data['unit']
        )
        db.session.add(composition)
        db.session.commit()
        return jsonify({'message': 'Composition created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    try:
        # TODO: Implement calculation logic
        return jsonify({'result': 'Calculation result will be here'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 