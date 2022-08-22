
# Introduction
基于pytesseract做文字识别，用opencv做图像识别，配合pyautogui操纵鼠标与键盘，可以用来做纯GUI bot.
pyautogui与xvfb结合，可以用来做浏览器与桌面应用测试，绕过Bot安全应用产品对浏览器运行环境的检查。

# 主要目的
不是做浏览器兼容性测试。而是绕过安全产品对运行环境以及鼠标轨迹的检查。

# 注意事项
图像匹配的时候，是用的matchTemplate并以TM_CCOEFF_NORMED进行匹配。适用于rotation, scale, and viewing angle恒定的情况.示例中，仅通过guacamole去launch ie/edge浏览器以及关闭浏览器的时候使用到图像匹配。示例中，是通过guacamole usermapping.xml的dispaly settings来强制width/height/rdp，以达到恒定。

# 被测浏览器支持情况
FF: 60+. 原因：60以前的，难以通过policies.json去控制DefaultBrowserCheck以及AutoUpdate.

Chrome: 48+

IE: 8-11, 基于微软提供的VM (通过Guacamole进行测试)

Edge: 微软提供的win10 VM (通过Guacamole进行测试)


# Build时候传入版本号速查
## Chrome 88+
https://www.ubuntuupdates.org/package/google_chrome/stable/main/base/google-chrome-stable
## Chome 88-
https://www.slimjet.com/chrome/google-chrome-old-version.php
## Firefox
https://download-installer.cdn.mozilla.net/pub/firefox/releases/

# 基本用法
## 前提条件
1. 测试网站运行
2. docker. 若需要借助guacamole做远程控制，则需要docker-compose.运行guacamole的机器可以是任意机器，只要测试脚本docker能够访问到即可。
## 浏览器 standalone bot

### 原理与适用场景
通过脚本启动浏览器进程，浏览器通过mixin带有文字识别与图像识别功能，并通过pyautogui发起键盘与鼠标事件.有点象sikuli.

此方式适合于测试此类型浏览器：浏览器可以在linux环境安装，如firefox,chrome. 使用方式脚本示例见examples/test_browser_standalone.py.
### 使用方法与步骤
1. build 带有测试浏览器与测试脚本的docker. build的时候需要传入BROWSER_NAME,与BROWSER_VERSION. 版本速查请参考[浏览器版本速查](#浏览器版本速查)
```bash
docker build . -t bot_click:chrome103 --build-arg BROWSER_NAME=Chrome --build-arg BROWSER_VERSION=103.0.5060.114-1
```
2. 准备环境变量，运行脚本docker
```bash
docker run --rm --env-file .env bot_click:chrome103 python examples/test_browser_standalone.py
```
> 若需要查看screenshot，请docker run的时候mount volume到/tmp/.debug 或者 /app/.debug. 文件夹.debug可任选，但必须在/tmp/ 或者 /app/，否则appuser没有权限.
必须的环境变量为：
```bash
TESTWEB=http://192.168.254.168/
BROWSER_NAME=Chrome
```
更多环境变量，参考[环境变量](#环境变量与作用)
## 用浏览器连接Guacamole+Guacamole环境

### 为什么使用Guacamole
当我们有很多实体机与VM需要远程访问与管理的时候，不管这些实体机/VM使用RDP,VNC,SSH，你只需要浏览器就可以访问，无需安装繁多的client: ssh client, vncclient,rdpclient等，一个浏览器就搞定。
在Bot中的应用：使用脚本配合虚拟出的键盘鼠标显示器，远程访问与控制受控机器，绕过安全产品对Bot的检查。
### 原理与适用场景
通过远程控制软件，去操作真实的未改变浏览器状态（selenium,webdriver等)的浏览器，绕过安全产品检查。

此方式适合于测试此类型浏览器：不方便在linux环境安装或者准备工作过于繁杂，或者已经有Guacamole环境。
使用方式脚本示例见examples/test_browser_in_guca.py.
### 已测试的浏览器支持情况
已测试:通过Firefox作为Guacamole的浏览器客户端，去访问WINDOWS VM中的ie8-11,edge.
#### 注意事项
请使用Firefox，不要使用Chrome.
原因:通过Chrome的policy去disable password manager并不生效。故推荐使用Firefox或者Chromium.

### 使用方法与步骤
1. build:与standalone是一样的，build参数也一致。目前已测支持Chrome以及Firefox。建议使用这两者，因为可以通过policy控制Password Manager的干扰。
```bash
docker build . -t bot_click:ff102 --build-arg BROWSER_NAME=Firefox --build-arg BROWSER_VERSION=102.0
```
2. 请确保vm/实体机提供了ssh/vnc/rdp支持远程连接。如：windows机器上面，勾选允许远程桌面连接功能（Allow connections only from computers running Remote Desktop with Network Level Authentication）
3. 修改docs/guaca_compose/config/user-mapping.xml中的受控机器ip与端口，并部署Guacamole环境。更多信息，请参考对应目录下的README.md.

> Guacamole docker compose环境应该部署在与受控机器网络可通的机器上，与测试脚本docker是独立的，可以在不同的机器上。

3.1 仅修改ip与端口就可以了。
3.2 guacamole docker compose
```bash
cd example_auxiliary/guaca_compose
docker-compose up -d
```
3.3 验证guacamole部署正确,参考对应目录下的帮助文档。
4. 传入环境变量，运行脚本docker。
```bash
docker run --rm --env-file .env bot_click:ff102 python examples/test_browser_in_guca.py
```
必须的环境变量
```bash
TESTWEB=http://192.168.254.168/
BROWSER_NAME=Firefox
GUACA_BROWSER=ie9
GUACA_URL=http://192.168.254.139:8080/guacamole/
```
更多环境变量，参考[环境变量](#环境变量与作用)
5. （可选):脚本开始时，自动启动VM；以及结束后自动关闭VM。
通常情况下，虚拟化平台都有提供restapi server来控制vm。
5.1 修改examples/libs/utils.py 中的vm_context中的url以及参数。
5.2 在运行脚本docker(step#4)的时候，传入额外参数:
```
VM_RESTAPI=http://192.168.254.139:8000
```
# 环境变量与作用
## 通用环境变量
| Name 	| Example 	| Comment 	|  	|
|---	|---	|---	|---	|
| DEBUG 	| 1 	| control log level; 	|  	|
| SCREENSHOTS_FOLDER 	| /tmp/.debug 	| Folder to save the screenshot，详见1,2 	|  	|
| BROWSER_NAME 	| Chrome 	| Standalone: test browser.<br>In Guacamole: the browser to access Guacamole 	|  	|
| TESTWEB 	| http://192.168.254.168/ 	| url to test website 	|  	|

1. 使用BrowserBot与WindowsBrowserScreen类时，当出现BotClickError的时候，会将screenshot保存在环境变量SCREENSHOTS_FOLDER指定位置
2. examples/test_browser_*.py 中，若DEBUG=1，且提供环境变量SCREENSHOTS_FOLDER，则会在用例的每次点击前，将点击处标记crosshair，保存到指定目录.
3. SCREENSHOTS_FOLDER指定目录以及你目录可以不存在。若不存在，会自动创建。但需保证脚本有写权限。

> 若需要查看screenshot，请docker run的时候mount volume到/tmp/.debug 或者 /app/.debug. 文件夹.debug可任选，但必须在/tmp/ 或者 /app/，否则appuser没有权限.
## 通过Guacamole远程执行时的环境变量
| Name 	| Example 	| Comment 	|  	|
|---	|---	|---	|---	|
| BROWSER_NAME 	| Chrome 	| Standalone: test browser.<br>In Guacamole: the browser to access Guacamole 	|  	|
| GUACA_URL 	| http://192.168.254.139:8080/guacamole/ 	| guacamole login url 	|  	|
| GUACA_BROWSER 	| ie8 	| browser under test. The browser is accessed via Guacamole 	|  	|
| VM_RESTAPI 	| http://192.168.254.139:8000 	| RESTful API server to control (start/stop) the vm 	|  	|

# 开发环境搭建
推荐安装与使用VS code的 Remote Container插件。repo中已经check in了IDE的配置，包括debug config, linting, formatting等。无须写冗长地如何搭建开发环境文档。而且，formatting与linting，包括pre-commit已经配置好，风格统一。
# 调试与排错
1. 参考环境变量一节中的配置.
3. 推荐安装与使用VS code的 Remote Container插件,会自动识别.devcontainer目录. devcontainer.json中已经配置好所有与VSCode相关的。包括debug config, lint, formatting.
4. 开发脚本阶段，通过修改.devcontainer/devcontainer.json中的remoteEnv修改环境变量，会对debug,run,terminal生效。若只是临时修改，直接在terminal中传入即可。
5. 打开VSCode的时候，由于pip install是在dev container创建完成后通过postCreateCommand安装，所以在pip完成以前，VSCode可能会提示未安装Lint/Black之类的，问是否要安装，你可以忽略这些提示。
6. 调试Python文件。devcontainer.json中已经配置好了，所以你就象平时调试Python文件一样：选定文件，点击窗口右上角的Debug Python File就可以了。
7. VSCode有时候会有黄色波浪线提示找不到module,打开VSCode的command palette(cmd+shift+p)，选择Python:Restart Lanauge Server就可以了。

# 参考资料
## 浏览器版本速查
浏览器版本速查：
- https://www.ubuntuupdates.org/package/google_chrome/stable/main/base/google-chrome-stable
- https://stackoverflow.com/questions/52217175/any-way-to-install-specific-older-chrome-browser-version
