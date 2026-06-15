# SMS Dashboard - 自用短信验证码面板

> 一个最小化的自托管短信验证码管理面板：安卓手机转发短信 → 服务器保存到 MySQL → 后台管理和客户验证码页展示

## 功能特点

- ✅ **Docker 一键部署** - `docker compose up -d` 即可运行
- ✅ **后台管理** - 手机号池、卡密管理、数据看板
- ✅ **客户验证码页** - 通过卡密链接查看验证码
- ✅ **闲管家对接** - 支持虚拟货源自动发货
- ✅ **Webhook 推送** - 支持公网部署
- ✅ **多手机支持** - 手机号池管理，设备 ID + SIM 卡槽路由

## 快速部署

### 方法一：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/kee5876/sms-dashboard.git
cd sms-dashboard

# 2. 创建配置文件
cp .env.example .env

# 3. 编辑配置（修改密码和地址）
nano .env

# 4. 启动服务
docker compose up -d --build

# 5. 查看状态
docker compose ps
docker compose logs -f
```

### 方法二：飞牛 NAS 部署

1. **上传项目到 NAS**
   - 在 NAS 文件管理中创建 `/docker/sms-dashboard` 目录
   - 上传项目所有文件到该目录

2. **创建配置文件**
   - 在 `/docker/sms-dashboard/` 目录下创建 `.env` 文件
   - 参考下方「配置文件说明」

3. **通过 Docker Compose 启动**
   - 打开 NAS 的 Docker 管理器
   - 进入「项目」或「Compose」标签
   - 新建项目，选择上传 `docker-compose.yml`
   - 确认 `.env` 文件在同一目录
   - 点击部署/启动

4. **访问后台**
   ```
   http://你的 NAS 内网 IP:8787
   ```

## 配置文件说明

复制 `.env.example` 为 `.env`，然后修改以下关键配置：

```bash
# 后台登录
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=请修改为你的后台登录密码

# Webhook 配置
WEBHOOK_TOKEN=请生成随机 token
WEBHOOK_SIGNING_KEY=请生成随机签名密钥

# 公网访问地址（局域网部署用内网 IP）
PUBLIC_BASE_URL=http://你的 NAS 内网 IP:8787

# MySQL 数据库
MYSQL_PASSWORD=请修改为你的 MySQL 用户密码
MYSQL_ROOT_PASSWORD=请修改为你的 MySQL root 密码

# Android SMS Gateway（手机和 NAS 需在同一局域网）
SMS_GATEWAY_BASE_URL=http://手机 IP:8080
SMS_GATEWAY_USER=手机 App 显示的用户名
SMS_GATEWAY_PASSWORD=手机 App 显示的密码
```

## 手机配置

1. **安装 Android SMS Gateway**
   - 下载地址：https://github.com/capcom6/android-sms-gateway/releases
   - 授权短信权限，开启 Local Server
   - 确保手机和 NAS 在同一 Wi-Fi/局域网

2. **记录手机信息**
   - IP 地址（如 `192.168.1.100`）
   - 用户名
   - 密码

3. **配置 .env**
   将手机信息填入 `.env` 文件，然后重启服务：
   ```bash
   docker compose restart sms-dashboard
   ```

## 使用指南

### 后台管理

1. 登录后进入 **手机号池**，添加接码手机号
2. 进入 **卡密管理**，创建客户卡密
3. 设置：项目名称、到期时间、可接码次数、过滤关键词
4. 复制客户链接发送给需要接码的人

### 客户验证码页

客户打开链接：
```
http://你的 NAS 内网 IP:8787/user?card=卡密
```
即可查看接收到的验证码。

## 目录结构

```
sms-dashboard/
├── app.py                 # 主程序
├── docker-compose.yml     # Docker 编排
├── Dockerfile            # Docker 镜像构建
├── .env.example          # 配置模板
├── .env                  # 实际配置（不提交到 Git）
├── requirements.txt      # Python 依赖
├── schema/               # 数据库初始化脚本
│   └── mysql.sql
├── static/               # 前端静态文件
│   ├── index.html        # 管理后台
│   └── user.html         # 客户验证码页
└── tests/                # 测试脚本
```

## 常用命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 重新构建
docker compose up -d --build

# 测试
python -m unittest discover -s tests -v
```

## 上传到 GitHub

```bash
# 1. 初始化 Git 仓库
cd sms-dashboard
git init

# 2. 添加所有文件
git add .

# 3. 提交
git commit -m "initial commit"

# 4. 创建 GitHub 仓库
# 5. 添加远程仓库并推送
git remote add origin https://github.com/kee5876/sms-dashboard.git
git branch -M main
git push -u origin main
```

以后就可以通过 `git clone` 拉取项目，直接 `docker compose up -d` 部署了！

## 注意事项

| 项目 | 说明 |
|------|------|
| **端口** | 默认 8787，可在 `.env` 修改 `PUBLIC_PORT` |
| **安全** | 不要直接暴露 8787 端口到公网，建议用 Nginx 反代 + HTTPS |
| **网络** | 手机和 NAS 必须同一局域网，或配置 Webhook 公网推送 |
| **备份** | 数据存在 Docker 卷里，定期导出备份 |

## License

MIT
