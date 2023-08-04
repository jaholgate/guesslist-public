// On button click
document.querySelector('.guess-form__button').addEventListener('click', function (event) {
	event.preventDefault();
	let guessesValid = true;
	let values = [];
	const guessInputs = document.querySelectorAll('.guess-form__input.select');

	for (const input of guessInputs) {
		val = input.value;
		if (val == 'Select:') {
			guessesValid = false;
			showError('Add a guess for each song');
			break;
		} else if (values.includes(val)) {
			guessesValid = false;
			showError('Guesses must be unique');
			break;
		} else {
			values.push(val);
		}
	}

	function showError(message) {
		document.querySelector('.js-error').classList.remove('hidden');
		document.querySelector('.js-error__text').innerHTML = message;
	}

	if (guessesValid) {
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
	}
});
