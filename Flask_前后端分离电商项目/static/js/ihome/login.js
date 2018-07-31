// function getCookie(name) {
//     var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
//     alert(r);
//     return r ? r[1] : undefined;
//     }
// $(document).ready(function() {
//     $("#mobile").focus(function(){
//         $("#mobile-err").hide();
//     });
//     $("#password").focus(function(){
//         $("#password-err").hide();
//     });
//     $(".form-login").submit(function(e){
//         // 因为html采取了form表单, 前后端分离, 无法使用表单发送数据, 所以改用ajax请求, 发送json格式数据, 进行局部更新
//         // 所有需要禁止submit 进行表单提交
//         e.preventDefault();
//         var mobile = $("#mobile").val();
//         var passwd = $("#password").val();
//         if (!mobile) {
//             $("#mobile-err span").html("请填写正确的手机号！");
//             $("#mobile-err").show();
//             return;
//         }
//         if (!passwd) {
//             $("#password-err span").html("请填写密码!");
//             $("#password-err").show();
//             return;
//         }
//         // 组织参数
//         var reqData = {
//             mobile:mobile,
//             password:passwd
//         };
//         // 将字典转化为json格式的数据
//         var JsonStr = JSON.stringify(reqData);
//         $.ajax({
//             url:"/api/v1.0/user/login", // 请求路径
//             type:"post", // 提交方式
//             data: JsonStr, //请求体数据
//             contentType:'application/json', //向后端说明请求体数据是json格式
//             dataType:'json', // 需要接收json格式的数据
//             headers:{
//               "X-CSRFToken": getCookie("csrf_token") // 添加自定义的请求头，为了配合后端的csrf验证 自定义在请求头中, 在后端, 当在请求体中无法找到从csrf_token时,就会到请求头中寻找
//             },
//             success: function (data) {
//                 if(data.errcode == '0') {
//                     location.href = '/index.html';
//                 }else{
//                     alert(data.errmsg);
//                 }
//             }
//         })
//     });
// });

function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(document).ready(function() {
    $("#mobile").focus(function(){
        $("#mobile-err").hide();
    });
    $("#password").focus(function(){
        $("#password-err").hide();
    });
    $(".form-login").submit(function(e){
        e.preventDefault();

        var mobile = $("#mobile").val();
        var passwd = $("#password").val();
        if (!mobile) {
            $("#mobile-err span").html("请填写正确的手机号！");
            $("#mobile-err").show();
            return;
        }
        if (!passwd) {
            $("#password-err span").html("请填写密码!");
            $("#password-err").show();
            return;
        }

        var reqData = {
            mobile: mobile,
            password: passwd
        };

        $.ajax({
            url: "/api/v1.0/user/login",
            type: "post",
            data: JSON.stringify(reqData),
            contentType: "application/json",
            dataType: "json",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            },
            success: function (resp) {
                if (resp.errcode == "0") {
                    location.href = "index.html";
                } else {
                    alert(resp.errmsg);
                }
            }
        })
    });
});
