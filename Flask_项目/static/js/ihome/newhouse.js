function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(document).ready(function(){
    // $('.popup_con').fadeIn('fast');
    // $('.popup_con').fadeOut('fast');
    // 向后端发送请求
    $.get("api/v1.0/area_info", function (data) {
        if (data.errcode == '0'){
            // 渲染模板
            //                         模板名         模板变量
            var area_html = template("areas-temp", {areas: data.data.area});
            // 填充到页面中
            $("#area-id").html(area_html);
        }else{
            alert(data.errmsg)
        }
    },"json")
});
