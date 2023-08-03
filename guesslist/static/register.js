const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const club_id = urlParams.get('club_id');
if (club_id) {
	document.querySelector('#club_id').value = club_id;
}
