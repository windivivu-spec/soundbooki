'use strict';
let deleteBookTarget=null,deleteBookTrigger=null,deleteUndoToken=null;
function showDeletedBook(value){
 deleteUndoToken=value?.undoToken||null;$('deletedBookNotice').hidden=!deleteUndoToken;
 if(value)$('deletedBookNotice').querySelector('[role=status]').textContent='Đã xóa “'+value.title+'” khỏi thư viện.';
}
function openDeleteBook(value,trigger){
 if(document.querySelector('dialog[open]'))return;
 deleteBookTarget=value;deleteBookTrigger=trigger;$('deleteBookName').textContent=value.title;$('deleteBookError').hidden=true;$('confirmDeleteBook').disabled=false;
 if(book?.id===value.id&&dirty){$('deleteBookError').textContent='Lưu hoặc hủy phần chỉnh sửa đang mở trước khi xóa sách.';$('deleteBookError').hidden=false;$('confirmDeleteBook').disabled=true;}
 $('deleteBookDialog').showModal();$('cancelDeleteBook').focus();
}
function handleLibraryEvent(e){
 if(e.event==='init'&&e.lastDeleted)showDeletedBook(e.lastDeleted);
 if(e.event==='error'&&e.action==='deleteBook'){$('deleteBookError').textContent=e.message;$('deleteBookError').hidden=false;$('confirmDeleteBook').disabled=false;return true;}
 if(e.event==='bookDeleted'){
  deleteUndoToken=e.undoToken;books=e.books;libraryKey='';
  if(book?.id===e.bookId){stop();book=null;selectedId=null;homeActive=true;awaitingImport=false;resetReader(null);$('reader').hidden=true;$('player').hidden=true;}
  $('deleteBookDialog').close();if(e.lastDeleted)showDeletedBook(e.lastDeleted);else $('deletedBookNotice').hidden=false;render();
  if(!book)$('undoDeleteBook').focus();
  return true;
 }
 if(e.event==='bookRestored'){
  books=e.books;libraryKey='';showDeletedBook(e.lastDeleted);renderBooks();selectBook(e.bookId);return true;
 }
 return false;
}
window.addEventListener('DOMContentLoaded',()=>{
 $('cancelDeleteBook').onclick=()=>$('deleteBookDialog').close();
 $('deleteBookDialog').onclose=()=>{if(deleteBookTrigger?.isConnected)deleteBookTrigger.focus();};
 $('confirmDeleteBook').onclick=()=>{if(!deleteBookTarget)return;if(book?.id===deleteBookTarget.id&&guardDirty())return;if(book?.id===deleteBookTarget.id){flushReader();stop();}$('confirmDeleteBook').disabled=true;send({action:'deleteBook',bookId:deleteBookTarget.id});};
 $('undoDeleteBook').onclick=()=>{if(deleteUndoToken)send({action:'restoreBook',undoToken:deleteUndoToken});};
 $('dismissDeletedBook').onclick=()=>$('deletedBookNotice').hidden=true;
});
