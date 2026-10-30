'use strict';
const $=id=>document.getElementById(id);let config,code='';
function message(value){$('message').textContent=value;}
function render(){
 if(!/^SN[A-F0-9]{12}$/.test(code)||!config?.salesReady)return;
 $('payment').hidden=false;const url=new URL(config.qrUrl);url.searchParams.set('addInfo',code);$('qr').src=url.href;
 $('bank').replaceChildren();for(const [label,value]of [['Ngân hàng',config.bank.bank],['Số tài khoản',config.bank.account],['Chủ tài khoản',config.bank.name],['Số tiền','189.000đ'],['Nội dung chuyển khoản',code]]){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;$('bank').append(dt,dd);}
}
$('requestForm').onsubmit=event=>{event.preventDefault();code=$('deviceCode').value.trim().toUpperCase();if(!/^SN[A-F0-9]{12}$/.test(code)){message('Sao chép đúng mã máy từ app.');return;}render();};
$('copyCode').onclick=async()=>{try{await navigator.clipboard.writeText(code);message('Đã sao chép nội dung.');}catch{message('Nội dung: '+code);}};
(async()=>{try{const response=await fetch('config.json');if(!response.ok)throw Error('Chưa đọc được cấu hình mua.');config=await response.json();$('salesState').textContent=config.salesReady?'Quay lại cửa sổ thanh toán trong app để tự nhận Pro sau khi giao dịch được xác nhận.':'Bản Pro đang chuẩn bị phát hành. Chưa chuyển khoản lúc này.';$('createRequest').disabled=!config.salesReady;const fragment=new URLSearchParams(location.hash.slice(1)).get('device')?.toUpperCase();if(fragment&&/^SN[A-F0-9]{12}$/.test(fragment)){code=fragment;$('deviceCode').value=code;render();}}catch(error){message(error.message);}})();
