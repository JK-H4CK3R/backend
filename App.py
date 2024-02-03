# alerts/app.py
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from binance.client import Client  # Install python-binance

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/dbname'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
app.config['CACHE_TYPE'] = 'redis'
app.config['CACHE_REDIS_URL'] = 'redis://localhost:6379/0'

jwt = JWTManager(app)
db = SQLAlchemy(app)
cache = Cache(app)

binance_api_key = 'your_binance_api_key'
binance_api_secret = 'your_binance_api_secret'
binance_client = Client(api_key=binance_api_key, api_secret=binance_api_secret)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='created')

@app.route('/alerts/create/', methods=['POST'])
@jwt_required()
def create_alert():
    data = request.get_json()
    user_id = get_jwt_identity()
    new_alert = Alert(user_id=user_id, target_price=data['target_price'])
    db.session.add(new_alert)
    db.session.commit()
    return jsonify(message='Alert created successfully'), 201

@app.route('/alerts/delete/<int:alert_id>/', methods=['DELETE'])
@jwt_required()
def delete_alert(alert_id):
    user_id = get_jwt_identity()
    alert = Alert.query.filter_by(id=alert_id, user_id=user_id).first()
    
    if alert:
        db.session.delete(alert)
        db.session.commit()
        return jsonify(message='Alert deleted successfully'), 200
    else:
        return jsonify(error='Alert not found'), 404

@app.route('/alerts/fetch/', methods=['GET'])
@jwt_required()
@cache.cached(timeout=60)  # Cache for 60 seconds
def fetch_alerts():
    user_id = get_jwt_identity()
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    status_filter = request.args.get('status')

    query = Alert.query.filter_by(user_id=user_id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    alerts = query.paginate(page=page, per_page=per_page, error_out=False)

    result = {
        'alerts': [
            {'id': alert.id, 'target_price': alert.target_price, 'status': alert.status}
            for alert in alerts.items
        ],
        'pagination': {
            'total_pages': alerts.pages,
            'current_page': alerts.page,
            'per_page': per_page,
            'total_alerts': alerts.total
        }
    }

    return jsonify(result), 200

if __name__ == '__main__':
    app.run(debug=True)
