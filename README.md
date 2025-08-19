# 微信风格聊天室

一个基于Flask和SocketIO的实时聊天室应用，具有微信风格的界面和用户注册登录功能。

## 功能特性

- 实时消息传递
- 微信风格的UI界面
- 用户注册和登录（邮箱验证码验证）
- 消息历史记录
- 在线用户统计

## 环境要求

- Python 3.7+
- MySQL数据库

## 安装步骤

1. 克隆项目代码：
   ```
   git clone <https://github.com/lvshenfx/liaotian.git>
   cd chat
   ```

2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

3. 配置环境变量：
   .env 并填写相应配置：
   ```
   
   编辑 `.env` 文件，填写以下信息：
   - 数据库连接信息
   - 邮箱配置（用于发送验证码）
   - Flask密钥

4. 初始化数据库：
   ```
   python create_complete_tables.py
   ```

5. 运行应用：
   ```
   python app.py
   ```

6. 访问应用：
   打开浏览器访问 `http://localhost:5000`

## 配置说明

### 数据库配置

在 `.env` 文件中配置以下变量：

- `DB_HOST`: 数据库主机地址
- `DB_USER`: 数据库用户名
- `DB_PASS`: 数据库密码
- `DB_NAME`: 数据库名称

### 邮箱配置

在 `.env` 文件中配置以下变量：

- `EMAIL_HOST`: SMTP服务器地址（默认为QQ邮箱）
- `EMAIL_PORT`: SMTP端口（默认为465）
- `EMAIL_USER`: 发件邮箱地址
- `EMAIL_PASS`: 邮箱密码或授权码

### Flask配置

在 `.env` 文件中配置以下变量：

- `SECRET_KEY`: Flask应用密钥

## 使用说明

1. 访问 `http://localhost:5000/login` 进行注册或登录
2. 注册时需要提供用户名和邮箱，并通过邮箱验证码验证
3. 登录时需要提供邮箱，并通过邮箱验证码验证
4. 登录成功后会自动跳转到聊天室页面

## 注意事项

- QQ邮箱需要开启SMTP服务并使用授权码作为密码
- 请确保数据库服务正常运行
- 请使用强随机字符串作为SECRET_KEY
