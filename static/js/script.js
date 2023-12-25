function sendTokenToServer(token) {
  fetch('/save_fcm_token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 'token': token }),
  })
    .then(response => {
      if (response.ok) {
        console.log('FCM token sent to Flask server successfully!');
        // Handle success if needed
      } else {
        console.error('Failed to send FCM token to Flask server');
        // Handle failure if needed
      }
    })
    .catch(error => {
      console.error('Error sending FCM token:', error);
    });
}


passwordField = document.getElementById('password')
checkbox = document.getElementById('show_password')

checkbox.addEventListener('change', ()=>{
    if (checkbox.checked) {
        passwordField.type = "text"
    }
    else{
        passwordField.type="password"
    }
})



function updateTodoStatus(checkbox){
    const todo_id = checkbox.value
    const completed = checkbox.checked
    console.log(completed)
    fetch(`/updatetodo/${todo_id}`,{
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body:JSON.stringify({ 'completed': completed })
    })
    .then(response =>{
        if (response.ok){
            console.log('Todo status updated successfully!');
        }
        else{
            console.error('Failed to update todo status');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
