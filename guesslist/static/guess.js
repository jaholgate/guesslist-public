// On button click
document.querySelector('.guess-form__button').addEventListener('click', function (event) {
	event.preventDefault();
	// TODO ensure guesses are unique
	// For each fieldset
	document.querySelectorAll('.guess-form__fieldset').forEach(fieldset => {
		// Create an empty array to store the values in
		let values = [];
		// For each input in the fieldset with given class
		fieldset.querySelectorAll('.guess-form__input').forEach(input => {
			// Push value to array
			values.push(input.value);
		});
		// Set value of hidden input to string containing all values
		fieldset.querySelector('.guess-form__input--all-values').value = values.toString();
	});
	// Submit the form
	document.querySelector('#guess-form').submit();
});
