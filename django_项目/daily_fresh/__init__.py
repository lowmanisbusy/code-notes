# 导入pymysql 就相当于一个mysql客户端
import pymysql
# 在mysql服务器中, 只认识mysqldb名字的客户端, 所以需要将的pymysql的名字进行更改
# 在另外一个第三方模块 MySQL-python 中, 名字就是mysqldb所以它就不用更改
pymysql.install_as_MySQLdb()
