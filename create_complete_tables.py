from sqlalchemy import create_engine, text, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime
import os

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# ── 数据库配置 ──
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'database': os.getenv('DB_NAME'),
    'charset': 'utf8mb4'
}

# 创建数据库连接
engine = create_engine(f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}")

# 定义ORM基类
Base = declarative_base()

# 定义User模型
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)

# 定义Message模型
class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    body = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# 创建表
def create_tables():
    print("正在创建数据库表...")
    Base.metadata.create_all(engine)
    print("数据库表创建完成！")

# 检查email列是否存在，如果不存在则添加
def add_email_column():
    with engine.connect() as conn:
        # 检查列是否存在
        result = conn.execute(text("SHOW COLUMNS FROM users LIKE 'email'"))
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            print("正在为users表添加email列...")
            # 添加email列
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255) UNIQUE AFTER username"))
            conn.commit()
            print("Email列添加成功！")
        else:
            print("Email列已存在于users表中。")

# 主函数
def main():
    try:
        # 创建表
        create_tables()
        
        # 添加email列（如果不存在）
        add_email_column()
        
        print("\n数据库初始化完成！")
        print("- users表：包含id、username、email字段")
        print("- messages表：包含id、user_id、body、timestamp字段")
        
    except Exception as e:
        print(f"数据库初始化失败：{e}")

if __name__ == '__main__':
    main()