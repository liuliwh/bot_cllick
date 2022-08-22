# 介绍
该部署包括guacamole 以及guacd。
当我们有很多实体机与VM需要远程访问与管理的时候，不管这些实体机/VM使用RDP,VNC,SSH，你只需要浏览器就可以访问，无需安装繁多的client: ssh client, vncclient,rdpclient等，一个浏览器就搞定。
在Bot中的应用：使用脚本配合虚拟出的键盘鼠标显示器，远程访问与控制受控机器，绕过安全产品对Bot的检查。
# 使用方法
请按需修改config/user-mapping.xml中的受控机器ip与端口，并部署Guacamole环境。
样例中有多台微软提供用于 Test IE11 and Microsoft Edge Legacy的VM，连接在139机器的不同端口是因为有在139机器上面做端口映射。如果你的VM是bridge方式的话，填上VM的ip，rdp默认为3389.
1. 请按需修改config/user-mapping.xml中的受控机器ip与端口。
user-mapping.xml中的authorize username与password是用于登录Guacamole的，不是VM的username和password. VM的username和password是在connection中定义.
这样，Guacamole与connection的对应关系就建立起来了。理论上一个user可以有多个connection. 但为了避免多选，就一一对应了。
2. 启动guacamole docker compose
```bash
cd docs/guaca_compose
docker-compose up -d
```
3. 验证guacamole部署正确:
a. 启动受控VM，如：启动ie8的机器.
b. 打开浏览器，访问guaca_compose运行机器的http://ip_guaca_compose:8080/guacamole/
> 因为在guacamole console是直接用tomcat war部署，前面没加nginx，所以访问的时候路径是在/guacamole/而不是/.

c. 登录: ie8/test
这时候你就可以通过浏览器去访问与控制ie8机器了.