from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from flask_session import Session
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import pytz
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import random
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ── 数据库配置 ──
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'database': os.getenv('DB_NAME'),
    'charset': 'utf8mb4'
}
engine = create_engine(f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}")
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ── 邮箱配置 ──
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT'))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')  # 从环境变量获取邮箱密码

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)

# 存储验证码的字典（实际项目中应使用Redis等缓存）
verification_codes = {}

def send_verification_code(email):
    """发送验证码到指定邮箱"""
    # 生成6位随机数字验证码
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # 保存验证码和过期时间（5分钟）
    verification_codes[email] = {
        'code': code,
        'expires': datetime.now() + timedelta(minutes=5)
    }
    
    # 发送邮件
    try:
        msg = MIMEText(f'您的验证码是: {code}，5分钟内有效。', 'plain', 'utf-8')
        # 使用简单的From头部格式，直接使用邮箱地址
        msg['From'] = EMAIL_USER
        msg['To'] = email
        msg['Subject'] = 'Chat Room Verification Code'
        
        server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [email], msg.as_string())
        server.quit()
        
        return True
    except Exception as e:
        print(f"发送邮件失败: {e}")
        return False

# ── ORM 模型 ──
class User(Base):
    __tablename__ = 'users'
    id       = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False)
    email    = Column(String(255), unique=True, nullable=False)  # 新增邮箱字段
    messages = relationship('Message', back_populates='user')

class Message(Base):
    __tablename__ = 'messages'
    id        = Column(Integer, primary_key=True, autoincrement=True)
    user_id   = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    body      = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: get_beijing_time().replace(tzinfo=None))  # 存储北京时间但不包含时区信息
    user = relationship('User', back_populates='messages')

# 若表不存在则自动创建（已有则跳过）
Base.metadata.create_all(bind=engine)

# ── Flask & SocketIO ──
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 工具：获取数据库会话
def get_db():
    return SessionLocal()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/api/register', methods=['POST'])
def register():
    """用户注册接口"""
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    
    # 参数验证
    if not username or not email:
        return jsonify({'success': False, 'message': '用户名和邮箱不能为空'}), 400
    
    if len(username) > 32:
        return jsonify({'success': False, 'message': '用户名长度不能超过32个字符'}), 400
    
    db = get_db()
    try:
        # 检查用户名是否已存在
        existing_user = db.query(User).filter_by(username=username).first()
        if existing_user:
            return jsonify({'success': False, 'message': '该用户名已被使用，请选择其他用户名'}), 400
        
        # 检查邮箱是否已存在
        existing_email = db.query(User).filter_by(email=email).first()
        if existing_email:
            return jsonify({'success': False, 'message': '该邮箱已被注册'}), 400
        
        # 发送验证码
        if send_verification_code(email):
            return jsonify({'success': True, 'message': '验证码已发送到您的邮箱'}), 200
        else:
            return jsonify({'success': False, 'message': '验证码发送失败，请稍后重试'}), 500
    except Exception as e:
        print(f"注册失败: {e}")
        return jsonify({'success': False, 'message': '注册失败，请稍后重试'}), 500
    finally:
        db.close()

@app.route('/api/verify_code', methods=['POST'])
def verify_code():
    """验证邮箱验证码接口"""
    data = request.get_json()
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()
    username = data.get('username', '').strip()
    
    # 参数验证
    if not email or not code or not username:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    
    # 检查验证码
    if email not in verification_codes:
        return jsonify({'success': False, 'message': '请先获取验证码'}), 400
    
    stored_code_info = verification_codes[email]
    
    # 检查验证码是否过期
    if datetime.now() > stored_code_info['expires']:
        del verification_codes[email]  # 删除过期验证码
        return jsonify({'success': False, 'message': '验证码已过期，请重新获取'}), 400
    
    # 验证验证码
    if stored_code_info['code'] != code:
        return jsonify({'success': False, 'message': '验证码错误'}), 400
    
    # 验证通过，创建用户
    db = get_db()
    try:
        user = User(username=username, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 删除已使用的验证码
        del verification_codes[email]
        
        # 将用户信息存储在session中
        session['user_id'] = user.id
        session['username'] = user.username
        
        return jsonify({
            'success': True, 
            'message': '注册成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }), 200
    except Exception as e:
        db.rollback()
        print(f"创建用户失败: {e}")
        return jsonify({'success': False, 'message': '注册失败，请稍后重试'}), 500
    finally:
        db.close()

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录接口"""
    data = request.get_json()
    email = data.get('email', '').strip()
    
    # 参数验证
    if not email:
        return jsonify({'success': False, 'message': '邮箱不能为空'}), 400
    
    db = get_db()
    try:
        # 检查邮箱是否存在
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return jsonify({'success': False, 'message': '该邮箱未注册'}), 400
        
        # 发送验证码
        if send_verification_code(email):
            # 将用户信息存储在session中
            session['user_id'] = user.id
            session['username'] = user.username
            return jsonify({
                'success': True, 
                'message': '验证码已发送到您的邮箱',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }), 200
        else:
            return jsonify({'success': False, 'message': '验证码发送失败，请稍后重试'}), 500
    except Exception as e:
        print(f"登录失败: {e}")
        return jsonify({'success': False, 'message': '登录失败，请稍后重试'}), 500
    finally:
        db.close()

@app.route('/api/login_verify', methods=['POST'])
def login_verify():
    """登录验证码验证接口"""
    data = request.get_json()
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()
    
    # 参数验证
    if not email or not code:
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    
    # 检查验证码
    if email not in verification_codes:
        return jsonify({'success': False, 'message': '请先获取验证码'}), 400
    
    stored_code_info = verification_codes[email]
    
    # 检查验证码是否过期
    if datetime.now() > stored_code_info['expires']:
        del verification_codes[email]  # 删除过期验证码
        return jsonify({'success': False, 'message': '验证码已过期，请重新获取'}), 400
    
    # 验证验证码
    if stored_code_info['code'] != code:
        return jsonify({'success': False, 'message': '验证码错误'}), 400
    
    # 验证通过，获取用户信息
    db = get_db()
    try:
        user = db.query(User).filter_by(email=email).first()
        if user:
            # 删除已使用的验证码
            del verification_codes[email]
            
            # 将用户信息存储在session中
            session['user_id'] = user.id
            session['username'] = user.username
            
            return jsonify({
                'success': True, 
                'message': '登录成功',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }), 200
        else:
            return jsonify({'success': False, 'message': '用户不存在'}), 400
    except Exception as e:
        print(f"登录验证失败: {e}")
        return jsonify({'success': False, 'message': '登录失败，请稍后重试'}), 500
    finally:
        db.close()

@socketio.on('connect')
def on_connect():
    # 检查用户是否已登录
    if 'user_id' not in session:
        return False
    
    db = get_db()
    try:
        # 获取最新的50条消息
        msgs = (
            db.query(Message)
            .join(User)
            .order_by(Message.timestamp.desc())
            .limit(50)
            .all()
        )
        # 反转列表，让最老的消息在前面，最新的在后面
        msgs.reverse()
        
        # 包含时间戳信息（转换为北京时间）
        history = [
            {
                "name": m.user.username, 
                "msg": m.body,
                "timestamp": BEIJING_TZ.localize(m.timestamp).isoformat()  # 将数据库时间转换为北京时区
            } 
            for m in msgs
        ]
        emit('history', history)
    except Exception as e:
        print(f"Error loading history: {e}")
        emit('history', [])
    finally:
        db.close()

@socketio.on('chat')
def handle_chat(data):
    # 从session获取用户信息
    if 'user_id' not in session:
        return
    
    user_id = session['user_id']
    username = session['username']
    
    msg = data.get('msg', '')
    
    if not msg:
        return
    
    # 保存消息到数据库
    db = get_db()
    try:
        # 获取当前用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        # 创建消息
        message = Message(user_id=user.id, body=msg)
        db.add(message)
        db.commit()
        
        # 广播消息
        emit('chat', {
            'name': username,
            'msg': msg,
            'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }, broadcast=True)
    except Exception as e:
        print(f"Error handling chat: {e}")
    finally:
        db.close()

# ── 启动 ──
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)