function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
    //python三目方法:   r[1] if r else None
}
$(document).ready(function(){
});
//当点击退出按钮时,执行logout()函数
function logout() {
    $.ajax({
    url:'api/v1.0/session',
    type:'delete',
    headers:{"X-CSRFToken":getCookie("csrf_token")},
    dataType:'json',
    success:function (data) {
        if( data.errcode == '0'){
            location.href = '/index.html'
        }
    }
    });
}