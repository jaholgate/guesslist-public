const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const club_id = urlParams.get('club');
if (club_id) {
	document.querySelector('#club').value = club_id;
}
