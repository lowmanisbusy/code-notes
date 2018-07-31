// function showSuccessMsg() {
//     $('.popup_con').fadeIn('fast', function() {
//         setTimeout(function(){
//             $('.popup_con').fadeOut('fast',function(){});
//         },1000)
//     });
// }
//
// $(document).ready(function () {
//     function getCookie(name) {
//     var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
//     alert(r);
//     return r ? r[1] : undefined;
//     }
//
//     $("#form-avator").submit(function (e) {
//         e.preventDefault();
//         // 利用jquery扩展jquery.form.min.jsz向后端发送表单数据,补充回调函数
//         $("#form-avatar").ajaxSubmit({
//             url: "api/v1.0/user/avatars",
//             type: "PUT",
//             dataType: "json",
//             headers: {
//                 "X-CSRFToken": getCookie('csrf_token')
//             },
//             success: function (data) {
//                 if (data.errcode == "4101"){
//                     // 用户未登录
//                     location.href = "/login.html";
//                 }else if (data.errcode == "0"){
//                     // 上传头像成功
//                     image_url = data.data.avatar_url;
//                     $("#user-avatar").attr("src", image_url);
//                 }else{
//                     alert(data.errmsg);
//                 }
//             }
//         })
//     });
//     $("#form-name").submit(function (e) {
//         e.preventDefault();
//         // 获取参数
//         var name = $("#user-name").val();
//
//         if (!name){
//             alert("请填写用户名");
//             return;
//         }
//         $("#form-name").ajaxSubmit({
//             url: "/api/v1.0/user/name",
//             type: 'post',
//             data: JSON.stringify({name:name}),
//             contentType: "application/json",
//             dataType:"json",
//             headers:{
//                 "X-CSRFToken": getCookie("csrf-token")
//             },
//             success: function (data) {
//                 if (data.errcode == "0"){
//                     $(".error-msg").hide();
//                     showSuccessMsg();
//                 }else if (data.errcode == "4003"){
//                     $(".error-msg").show()
//                 }else{
//                     alert(data.errmsg)
//                 }
//             }
//         })
//     })
// });

function showSuccessMsg() {
    $('.popup_con').fadeIn('fast', function() {
        setTimeout(function(){
            $('.popup_con').fadeOut('fast',function(){});
        },1000)
    });
}

function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(document).ready(function () {
    // 在页面加载是向后端查询用户的信息
    $.get("/api/v1.0/user", function(resp){
        // 用户未登录
        if (resp.errcode == "4101") {
            location.href = "/login.html";
        }
        // 查询到了用户的信息
        else if (resp.errcode == "0") {
            $("#user-name").val(resp.data.name);
            if (resp.data.avatar) {
                $("#user-avatar").attr("src", resp.data.avatar);
            }
        }
    }, "json");

    $("#form-avatar").submit(function (e) {
        e.preventDefault();

        // 利用jquery扩展jquery.form.min.js向后端发送表单数据，补充回调函数
        $("#form-avatar").ajaxSubmit({
            url: "/api/v1.0/users/avatars",
            type: "post",
            dataType: "json",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            },
            success: function (resp) {
                if (resp.errcode == "4101") {
                    // 用户未登录
                    location.href = "/login.html";
                } else if (resp.errcode == "0") {
                    // 上传头像成功
                    image_url = resp.data.avatar_url;
                    $("#user-avatar").attr("src", image_url);
                } else {
                    alert(resp.errmsg);
                }
            }
        })
    });

    $("#form-name").submit(function(e){
        e.preventDefault();
        // 获取参数
        var name = $("#user-name").val();

        if (!name) {
            alert("请填写用户名！");
            return;
        }
        $.ajax({
            url:"/api/v1.0/user/name",
            type:"put",
            data: JSON.stringify({name: name}),
            contentType: "application/json",
            dataType: "json",
            headers:{
                "X-CSRFTOKEN":getCookie("csrf_token")
            },
            success: function (data) {
                if (data.errcode == "0") {
                    $(".error-msg").hide();
                    showSuccessMsg();
                } else if (data.errcode == "4001") {
                    $(".error-msg").show();
                } else if (data.errcode == "4101") {
                    location.href = "/login.html";
                }
            }
        });
    })
});

