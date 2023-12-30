import cptools
from corpwechatbot.app import AppMsgSender
from pysnmp.hlapi import *
import atexit
import schedule
import time

snmpip="192.168.255.130" #ups的ip
ups_statue="0"
ups_alert="0"
send_to=["admin"]
wework = AppMsgSender(corpid='',  # 你的企业id
    corpsecret='',  # 你的应用凭证密钥
    agentid='' # 你的应用id
    ) 


upsOutputSource={"2":"无输出（关机？）","3":"市电","4":"旁路（市电直通）","5":"电池"}
################众所周知的警报表
upsAlarmDescr={"1.3.6.1.2.1.33.1.6.3.1":"电池坏",#已确定需要更换一节或多节电池。
    "1.3.6.1.2.1.33.1.6.3.2":"UPS 从电池获取电力",
    "1.3.6.1.2.1.33.1.6.3.3":"UPS 电池电量低",
    "1.3.6.1.2.1.33.1.6.3.4":"UPS 电池耗尽",#当市电断电时，UPS 将无法维持当前负载。
    "1.3.6.1.2.1.33.1.6.3.5":"温度超出耐受范围",#
    "1.3.6.1.2.1.33.1.6.3.6":"市电供电故障",#输入条件超出容差。
    "1.3.6.1.2.1.33.1.6.3.7":"输出电压不良",#输出条件（OutputOverload 除外）超出容差。
    "1.3.6.1.2.1.33.1.6.3.8":"输出过载",#输出负载超过 UPS 输出容量。
    "1.3.6.1.2.1.33.1.6.3.9":"旁路运行",#旁路目前正在 UPS 上运行。
    "1.3.6.1.2.1.33.1.6.3.10":"旁路不良",#旁路超出容限。
    "1.3.6.1.2.1.33.1.6.3.11":"UPS 计划关机",#PS 已按请求关闭，即输出关闭。
    "1.3.6.1.2.1.33.1.6.3.12":"UPS 已关机",#整个 UPS 已按照命令关闭。
    "1.3.6.1.2.1.33.1.6.3.13":"故障：无法充电",#在UPS 充电器子系统中检测到未纠正的问题。
    "1.3.6.1.2.1.33.1.6.3.14":"关闭输出，由于上述原因",#UPS 的输出处于关闭状态。
    "1.3.6.1.2.1.33.1.6.3.15":"关闭系统，由于上述原因",#UPS 系统处于关闭状态。
    "1.3.6.1.2.1.33.1.6.3.16":"风扇故障",#检测到 UPS 中的一个或多个风扇发生故障。
    "1.3.6.1.2.1.33.1.6.3.17":"保险丝故障",#检测到一根或多根保险丝故障。
    "1.3.6.1.2.1.33.1.6.3.18":"一般故障",#检测到 UPS 存在一般故障。
    "1.3.6.1.2.1.33.1.6.3.19":"诊断测试失败",#最后一次诊断测试的结果表明失败。
    "1.3.6.1.2.1.33.1.6.3.20":"通讯故障（SNMP卡内部通讯失败）",#代理与 UPS 之间的通信遇到问题。
    "1.3.6.1.2.1.33.1.6.3.21":"关闭输出，将在市电恢复后重启",#UPS 输出关闭，UPS 正在等待输入电源恢复。
    "1.3.6.1.2.1.33.1.6.3.22":"UPS 已计划关机",#upsShutdownAfterDelay 倒计时正在进行中。
    "1.3.6.1.2.1.33.1.6.3.23":"UPS 即将关机",#UPS 将在 5 秒内关闭负载电源；这可能是定时关机或低电量关机。
    "1.3.6.1.2.1.33.1.6.3.24":"正在自检测试"#    1    1    正如测试组发起和指示的，测试正在进行中。通过其他特定于实现的机制启动的测试......
    }


def get_ups_value(oid):
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
               CommunityData('public', mpModel=0),
               UdpTransportTarget((snmpip, 161)),
               ContextData(),
               ObjectType(ObjectIdentity(oid)))
    )
    if errorIndication:
        print(f"Error: {errorIndication}")
        return None
    elif errorStatus:
        print(f"Error: {errorStatus.prettyPrint()}")
        return None
    else:
        #for varBind in varBinds:
            #print(f"{varBinds[0][0]} = {varBinds[0][1]}")
            return varBinds[0][1]

def get_ups_data():
    global ups_statue
    global ups_alert
    ups_now=str(get_ups_value("1.3.6.1.2.1.33.1.4.1.0"))
    ups_alert_now=str(get_ups_value("1.3.6.1.2.1.33.1.6.1.0"))
    if ups_statue!=ups_now or ups_alert!=ups_alert_now: #状态变化
        ups_statue=ups_now
        ups_alert=ups_alert_now
        msg="====UPS 监控通知====\n"
        msg=msg+"当前供电方式："+upsOutputSource.get(ups_statue, ups_statue)+"\n"
        msg=msg+"电池电量："+str(get_ups_value("1.3.6.1.2.1.33.1.2.6.0"))+"%\n"
        if ups_statue=="5":  #电池供电
            msg=msg+"估计电池供电时间："+str(get_ups_value("1.3.6.1.2.1.33.1.2.3.0"))+"分钟\n"
        else: #不是电池供电
            msg=msg+"市电电压："+str(get_ups_value("1.3.6.1.2.1.33.1.3.3.1.3.0"))+","+str(get_ups_value("1.3.6.1.2.1.33.1.3.3.1.3.1"))+","+str(get_ups_value("1.3.6.1.2.1.33.1.3.3.1.3.2"))+"\n"
            msg=msg+"估计充电所需时间："+str(get_ups_value("1.3.6.1.2.1.33.1.2.4.0"))+"分钟\n"
        if int(ups_alert)>0:
            msg=msg+"当前警报：\n"
            for i in range(1,int(ups_alert)+1):
                alm=str(get_ups_value("1.3.6.1.2.1.33.1.6.2.1.2."+str(i)))
                print(alm,upsAlarmDescr.get(alm,alm))
                msg=msg+"·"+upsAlarmDescr.get(alm,alm)+"\n"
        wework.send_text(content=msg.rstrip('\n'),touser=send_to)

def exit_alert():
    msg="==UPS 监控程序退出（由于关机或其他原因）==\n"
    msg=msg+"当前供电方式："+upsOutputSource.get(ups_statue, ups_statue)+"\n"
    wework.send_text(content=msg.rstrip('\n'),touser=send_to)






ups_statue=str(get_ups_value("1.3.6.1.2.1.33.1.4.1.0"))
ups_alert=str(get_ups_value("1.3.6.1.2.1.33.1.6.1.0"))
msg="==UPS 监控程序启动==\n"
msg=msg+"当前供电方式："+upsOutputSource.get(ups_statue, ups_statue)+"\n"
msg=msg+"电池电量："+str(get_ups_value("1.3.6.1.2.1.33.1.2.6.0"))+"%\n"
if ups_statue=="5":  #电池供电
    msg=msg+"估计电池供电时间："+str(get_ups_value("1.3.6.1.2.1.33.1.2.3.0"))+"分钟\n"
else: #不是电池供电
    msg=msg+"市电电压："+str(get_ups_value("1.3.6.1.2.1.33.1.3.3.1.3.0"))+","+str(get_ups_value("1.3.6.1.2.1.33.1.3.3.1.3.1"))+","+str(get_ups_value("1.3.6.1.2.1.33.1.3.3.1.3.2"))+"\n"
    msg=msg+"估计充电所需时间："+str(get_ups_value("1.3.6.1.2.1.33.1.2.4.0"))+"分钟\n"
if int(ups_alert)>0:
    msg=msg+"当前警报：\n"
    for i in range(1,int(ups_alert)+1):
        alm=str(get_ups_value("1.3.6.1.2.1.33.1.6.2.1.2."+str(i)))
        print(alm,upsAlarmDescr.get(alm,alm))
        msg=msg+"·"+upsAlarmDescr.get(alm,alm)+"\n"
wework.send_text(content=msg.rstrip('\n'),touser=send_to)


atexit.register(exit_alert)
schedule.every(1).minutes.do(get_ups_data)

while True:
    schedule.run_pending()
    time.sleep(1)

################常用查询
#   ups_oid = "1.3.6.1.2.1.33.1.2.3.0" #估计电池剩余时间（分钟
#   ups_oid = "1.3.6.1.2.1.33.1.2.4.0" #充电所需时间
#   ups_oid = "1.3.6.1.2.1.33.1.2.6.0" #电池电量%
#   ups_oid = "1.3.6.1.2.1.33.1.3.3.1.3.0" #第0号线路输入电压
#   ups_oid = "1.3.6.1.2.1.33.1.3.3.1.3.1" #第1号线路输入电压
#   ups_oid = "1.3.6.1.2.1.33.1.3.3.1.3.2" #第2号线路输入电压
#   ups_oid = "1.3.6.1.2.1.33.1.4.1.0" #ups输出源 3=正常 4=旁路 5=电池
#   ups_oid = "1.3.6.1.2.1.33.1.4.4.1.2.0" #输出电压
#   ups_oid = "1.3.6.1.2.1.33.1.4.4.1.5.0" #负载%
#   ups_oid = "1.3.6.1.2.1.33.1.6.1.0" #当前警报数量
#   ups_oid = "1.3.6.1.2.1.33.1.6.2.1.2.0" #警报1
#   ups_oid = "1.3.6.1.2.1.33.1.6.2.1.2.1" #警报2