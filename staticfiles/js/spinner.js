function showLoaderOnClick(div_id, form_id, btn_id) {
    showLoader(div_id, btn_id);
    document.getElementById(form_id).submit();
}
function showLoader(div_id, btn_id){
  const d = document.getElementById(div_id);
  const b = document.getElementById(btn_id)
  b.innerText = 'Submitting job, please wait...';
  b.disabled = true;
  d.innerHTML = '<div class="spinner-border text-primary"></div>' + d.innerHTML
  console.log(d);
}