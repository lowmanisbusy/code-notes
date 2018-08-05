# kafka是一种高吞吐量的分布式发布订阅消息系统，它可以处理消费者规模的网站中的所有动作流数据。 这种动作（网页浏览，搜索和其他用户的行动）
# 是在现代网络上的许多社会功能的一个关键因素。 这些数据通常是由于吞吐量的要求而通过处理日志和日志聚合来解决。 对于像Hadoop的一样的日志数据和离线分析系统，
# 但又要求实时处理的限制，这是一个可行的解决方案。Kafka的目的是通过Hadoop的并行加载机制来统一线上和离线的消息处理，也是为了通过集群来提供实时的消费。
#
# 特性：
# 通过O(1)的磁盘数据结构提供消息的持久化，这种结构对于即使数以TB的消息存储也能够保持长时间的稳定性能。
# 高吞吐量[2]：即使是非常普通的硬件Kafka也可以支持每秒数百万[2]  的消息
# 支持通过Kafka服务器和消费机集群来分区消息
# 支持Hadoop并行数据加载
#
# 术语：
# Broker
# Kafka集群包含一个或多个服务器，这种服务器被称为broker
# Topic
# 每条发布到Kafka集群的消息都有一个类别，这个类别被称为Topic。（物理上不同Topic的消息分开存储，逻辑上一个Topic的消息虽然保存于一个或多个broker上但用户只需指定消息的Topic即可生产或消费数据而不必关心数据存于何处）
# Partition
# Partition是物理上的概念，每个Topic包含一个或多个Partition.
# Producer
# 负责发布消息到Kafka broker
# Consumer
# 消息消费者，向Kafka broker读取消息的客户端。
# Consumer Group
# 每个Consumer属于一个特定的Consumer Group（可为每个Consumer指定group name，若不指定group name则属于默认的group）。

# 一、安装
# 在pypi.python.org有很多关于操作kafka的组件，我们选择weight最高的kafka1.3.5
# 1、有网的情况下执行如下命令安装:
# pip install kafka
# easy_install kafka
#
# 2、无网的情况下把源码下载下来，上传到需要安装的主机
# 压缩包: kafka - 1.3.5.tar.gz
# 解压: tar xvf kafka - 1.3.5.tar.gz
# 执行安装命令: cd kafka - 1.3.5
# python setup.py install
#
# 如安装报依赖错误，需要把依赖的组件也下载下来，然后进行安装，同样的方法，不赘述！

# kafka的设计模式属于生产者,消费者模式
# celery 也属于这种设计模式,celery是解决属于一个异步队列任务系统,用来处理耗时阻塞的任务


import time

from kafka import (
    KafkaProducer,
    KafkaConsumer,
    TopicPartition
)


# 创建一个生产者
def make_producer():
    # 此处ip可以是多个['0.0.0.1:9092','0.0.0.2:9092','0.0.0.3:9092' ]
    producer = KafkaProducer(bootstrap_servers=['172.21.10.136:9092'])
    for i in range(3):
        # 循环生产3条数据
        msg = "=========={}".format("build msg")
        # 将消息发送至broker,第一个参数topic,每条数据都必须有一个topic, 拉取数据时使用到
        producer.send("lowman", msg)
    producer.close()


# 创建一个消费者(简单demo)
def make_consumer():
    # 第一个参数是 topic, 可以传递多个topic 放在列表里如["lowman", "9527"]
    consumer = KafkaConsumer(
        "lowman",
        bootstrap_servers=['172.21.10.136:9092']
    )
    # 返回的是一个迭代器
    for message_obj in consumer:
        print("{}{}{}{}{}".format(
            message_obj.topic,
            message_obj.partition,
            message_obj.offset,
            message_obj.key,
            message_obj.value,
        )
        )


# 消费群组, group_id
# 启动多个消费者以后,只有满足相应的group_id的消费者才可以消费到,消费组可以横向扩展提高处理能力
def make_group_consumer():
    # 第一个参数是 topic, 可以传递多个topic 放在列表里如["lowman", "9527"]
    consumer = KafkaConsumer(
        "lowman",
        group_id="my-group",
        bootstrap_servers=['172.21.10.136:9092']
    )
    # 返回的是一个迭代器
    for message_obj in consumer:
        print("{},{},{},{},{}".format(
            message_obj.topic,
            message_obj.partition,
            message_obj.offset,
            message_obj.key,
            message_obj.value,
        )
        )


# 消费者 读取目前最早可读的消息
def make_early_consumer():
    # 第一个参数是 topic, 可以传递多个topic 放在列表里如["lowman", "9527"]
    # auto_offset_reset:重置偏移量，earliest移到最早的可用消息，latest最新的消息，默认为latest
    # 源码定义:{'smallest': 'earliest', 'largest': 'latest'}
    consumer = KafkaConsumer(
        "lowman",
        auto_offset_reset="earliest",
        bootstrap_servers=['172.21.10.136:9092']
    )
    # 返回的是一个迭代器
    for message_obj in consumer:
        print("{},{},{},{},{}".format(
            message_obj.topic,
            message_obj.partition,
            message_obj.offset,
            message_obj.key,
            message_obj.value,
        )
        )


# 消费者 手动设置偏移量
def make_handle_ass_consumer():
    consumer = KafkaConsumer('test',
                             bootstrap_servers=['172.21.10.136:9092'])

    print(consumer.partitions_for_topic("test"))  # 获取test主题的分区信息
    print(consumer.topics())  # 获取主题列表
    print(consumer.subscription())  # 获取当前消费者订阅的主题
    print(consumer.assignment())  # 获取当前消费者topic、分区信息
    print(consumer.beginning_offsets(consumer.assignment()))  # 获取当前消费者可消费的偏移量
    consumer.seek(TopicPartition(topic=u'test', partition=0), 5)  # 重置偏移量，从第5个偏移量消费
    for message in consumer:
        print("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                             message.offset, message.key,
                                             message.value))


# 消费者 订阅多个主题
def consumer_many_topic():
    consumer = KafkaConsumer(bootstrap_servers=['172.21.10.136:9092'])
    consumer.subscribe(topics=('test', 'test0'))  # 订阅要消费的主题
    print(consumer.topics())
    print(consumer.position(TopicPartition(topic=u'test', partition=0)))  # 获取当前主题的最新偏移量
    for message in consumer:
        print("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                             message.offset, message.key,
                                             message.value))


# 消费者 手动拉取消息
def consumer_get_msg():
    consumer = KafkaConsumer(bootstrap_servers=['172.21.10.136:9092'])
    consumer.subscribe(topics=('test', 'test0'))
    while True:
        msg = consumer.poll(timeout_ms=5)  # 从kafka获取消息
        print(msg)
        time.sleep(1)


# 消费者 消息的挂起与恢复
def consumer_hand_msg():
    # pause执行后，consumer不能读取，直到调用resume后恢复。
    consumer = KafkaConsumer(bootstrap_servers=['172.21.10.136:9092'])
    consumer.subscribe(topics=("test"))
    consumer.topics()
    consumer.pause(TopicPartition(topic='test', partition=0))
    num = 0
    while True:
        print(num)
        print(consumer.paused())  # 获取当前挂起的消费者
        msg = consumer.poll(timeout_ms=5)
        print(msg)
        time.sleep(2)
        num = num + 1
        if num == 10:
            print("resume...")
            consumer.resume(TopicPartition(topic='test', partition=0))
            print("resume......")
