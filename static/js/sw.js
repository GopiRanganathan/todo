self.addEventListener('push', event => {

  const options = {
    body: event.data.text(), 
    icon: '/static/images/TODO.png',
  };
 
  event.waitUntil(
    self.registration.showNotification('TODO', options) 
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  clients.openWindow('/'); 
});
