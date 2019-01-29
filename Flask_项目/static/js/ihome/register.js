// 这个函数是为了获取cookiez中的csrf_token, 因为在html中不再使用form进行表单提交
// 改用ajax提交, 所以请求体中不再带有csrf_token, 需要获取cookie中的csrf_token然后进行手动提交
// 使用到了正则匹配
function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

var imageCodeId = "";

function generateUUID() {
    var d = new Date().getTime();
    if(window.performance && typeof window.performance.now === "function"){
        d += performance.now(); //use high-precision timer if available
    }
    var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = (d + Math.random()*16)%16 | 0;
        d = Math.floor(d/16);
        return (c=='x' ? r : (r&0x3|0x8)).toString(16);
    });
    return uuid;
}

function generateImageCode() {
    // 向后端请求图片验证码
    // 生成验证码图片的编号
    // 直接在html页面中使用js不断动态生成验证码编号, 然后生成请求路径, 并添加到相应的img src = '' 中,浏览器就会向后端发送请求
    imageCodeId = generateUUID();

    // 拼接验证码图片的路径（即，后端的请求路径)
    var url = "/api/v1.0/image_codes/" + imageCodeId;

    // 设置到前端页面中
    $(".image-code img").attr("src", url);
}

function sendSMSCode() {
    // 当用户点击了一次之后, 将这个事件先移除, 防止用户进行了连击, 等60秒以后再进行事件回复
    // 虽然端对60秒内重发短信进行了限制, 但是如果用户进行连击, 就会短时间产生大量请求
    // 占用服务器资源
    $('.phonecode-a').removeAttr('onclick');
    var mobile = $('#mobile').val();
    if (!mobile) {
        $("#mobile-err span").html("请填写正确的手机号！");
        $("#mobile-err").show();
        $(".phonecode-a").attr("onclick", "sendSMSCode();");
        return;
    } 
    var imageCode = $("#imagecode").val();
    if (!imageCode) {
        $("#image-code-err span").html("请填写验证码！");
        $("#image-code-err").show();
        $(".phonecode-a").attr("onclick", "sendSMSCode();");
        return;
    }
    var repData = {
        image_code_id: imageCodeId,
        image_code_text: imageCode

    };
    $.get("/api/v1.0/sms_codes/" + mobile, repData,function(data){
        // 因为后端返回的响应数据是json字符串，并且包含了响应头Content-Type指明是application/json
        // 所以ajax会将收到的响应数据自动转换为js中的对象（字典），我们可以直接按照对象属性的操作获取返回数据
        // resp.errcode
        // resp.errmsg
        // 根据后端返回的不同错误编号，做不同的处理
        if (data.errcode == '0') {
            alert('短信验证码发送成功, 请注意查收');
            // 这里是否应该是不管是否发送成功, 都应该在第一次点击后,立马显示倒计时, 如果发送成功就进行局部更新提示发送成功,失败就在页面局部更新发送失败
            // 表示发送成功
            // 显示倒计时
            var num = 60;
            // 设定一定定时器, 每隔一秒钟就执行一下定时器在第一个参数中定义的函数,
            // 第二个参数是1000毫秒运行一次, 也就是1秒运行一次
            // 第三个参数是为了兼容IE浏览器的
            var timer = setInterval(function () {
                // num自减
                num--;
                if (num > 0) {
                    $(".phonecode-a").html(num+'秒');
                } else {
                    $(".phonecode-a").html("获取验证码");
                    $(".phonecode-a").attr("onclick", "sendSMSCode();");
                    // 清除定时器
                    clearInterval(timer);
                }
            }, 1000, 60);
        }else {
            alert(data.errmsg);
            $(".phonecode-a").attr("onclick", "sendSMSCode();");
        }
    });
}

$(document).ready(function() {
    generateImageCode();
    $("#mobile").focus(function(){
        $("#mobile-err").hide();
    });
    $("#imagecode").focus(function(){
        $("#image-code-err").hide();
    });
    $("#phonecode").focus(function(){
        $("#phone-code-err").hide();
    });
    $("#password").focus(function(){
        $("#password-err").hide();
        $("#password2-err").hide();
    });
    $("#password2").focus(function(){
        $("#password2-err").hide();
    });
    // 因为不再进行表单提交, 改用ajax提交, 所以需要阻挡submit进行默认的提交方式
    $(".form-register").submit(function(e){
        e.preventDefault();

        mobile = $("#mobile").val();
        phoneCode = $("#phonecode").val();
        passwd = $("#password").val();
        passwd2 = $("#password2").val();
        if (!mobile) {
            $("#mobile-err span").html("请填写正确的手机号！");
            $("#mobile-err").show();
            return;
        } 
        if (!phoneCode) {
            $("#phone-code-err span").html("请填写短信验证码！");
            $("#phone-code-err").show();
            return;
        }
        if (!passwd) {
            $("#password-err span").html("请填写密码!");
            $("#password-err").show();
            return;
        }
        if (passwd != passwd2) {
            $("#password2-err span").html("两次密码不一致!");
            $("#password2-err").show();
            return;
        }

        // 组织参数
        var reqData = {
            mobile:mobile,
            sms_code:phoneCode,
            password:passwd,
            password_checked:passwd2
        };
        //将参数转换为json格式的数据
        var reqJsonstr = JSON.stringify(reqData);

        // 因为需要定义请求头的数据, 所以需要使用完整的ajax的编写方式
        $.ajax({
            url:"/api/v1.0/user/register",
            type:"post",
            data:reqJsonstr, // 这是请求体数据
            contentType:"application/json", // 向后端说明请求体的数据是json格式
            dataType:"json",
            headers: {"X-CSRFToken": getCookie("csrf_token")// 添加自定义的请求头，为了配合后端的csrf验证
            },
            // 浏览器注册信息提交成功
            success: function (data) {
                // 根据后端返回的响应值，做不同的处理
                if (data.errcode == '0'){
                    // 注册成功跳转到主页
                    location.href = '/index.html';
                }else{
                    alert(data.errmsg);
                }
            },
            // 浏览器注册信息提交失败
            fail: function () {
                alert('注册信息提交失败');
            }
        });

    });
});