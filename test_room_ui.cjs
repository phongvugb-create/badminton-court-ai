const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const toasts = [], sounds = [];
const listeners = {};
const context = vm.createContext({
  console, Set, Date, Event: class {},
  document: { hidden: false, addEventListener(name, fn) { listeners[name] = fn; }, getElementById() { return null; } },
  window: {}, MockData: { facilities: [], matchmaking_rooms: [], notifications: [] },
  saveMockDataToLocalStorage() { return Promise.resolve(); },
});
vm.runInContext(fs.readFileSync('js/app.js', 'utf8') + '\nglobalThis.TestApp = BadmintonAIApp;', context);
const app = new context.TestApp();
app.currentUser = { id: 1, name: 'Host' };
app.showToast = text => toasts.push(text);
app.playNotificationChime = () => sounds.push(true);
app.updateHeaderNotificationBadge = () => {};
const n = { id: 'n1', type: 'ROOM_CHAT_MESSAGE', recipient_id: 1, room_id: 7, title: 'Phòng #3', content: 'Player 2: Xin chào', is_read: false };
context.MockData.notifications = [n];
// Notifications work outside the chat, once per event, never for another recipient.
app.handleLiveSyncEvent = context.TestApp.prototype.handleLiveSyncEvent.bind(app);
app.handleRoomNotification(n);
app.handleRoomNotification(n);
assert.equal(toasts.length, 1);
assert.equal(sounds.length, 1);
app.handleRoomNotification({ ...n, id: 'n2', recipient_id: 9 });
assert.equal(toasts.length, 1);
// Opening an active room marks its notices read without a distracting toast.
app.currentView = 'ui-07';
app.activeRoom = { id: 7 };
app.handleRoomNotification({ ...n, id: 'n3' });
assert.equal(toasts.length, 1);
assert.equal(n.is_read, true);
// Hidden tabs retain unread events.
context.document.hidden = true;
const hidden = { ...n, id: 'n4', is_read: false };
context.MockData.notifications.push(hidden);
app.handleRoomNotification(hidden);
assert.equal(hidden.is_read, false);
assert.equal(toasts.length, 2);
// SSE acknowledgement updates the local pending row without duplicate messages.
const room = { id: 7, chat_messages: [{ id: 'm1', text: 'hi', delivery_state: 'pending' }] };
context.MockData.matchmaking_rooms = [room];
app.currentView = 'ui-02';
app.receiveRoomChatMessage(7, { id: 'm1', text: 'hi', sender: 'Player 2', sender_id: 2 });
assert.equal(room.chat_messages.length, 1);
assert.equal(room.chat_messages[0].delivery_state, 'sent');
assert.equal(app.escapeRoomText('<img onerror="bad">'), '&lt;img onerror=&quot;bad&quot;&gt;');

(async () => {
  context.fetch = async () => ({ ok: false, status: 500 });
  const message = { id: 'm2', text: 'test', sender: 'Host' };
  await app.publishRoomChatMessage(7, message);
  assert.equal(message.delivery_state, 'failed');
  context.fetch = async () => ({ ok: true, json: async () => ({ message: { ...message, sender_id: 1 } }) });
  await app.publishRoomChatMessage(7, message);
  assert.equal(message.delivery_state, 'sent');
  assert.equal(room.chat_messages.filter(m => m.id === 'm2').length, 1);
  context.fetch = async () => ({ ok: false, json: async () => ({ detail: 'Phòng đã đầy' }) });
  const before = room.chat_messages.length;
  assert.equal(await app.joinRoomOnServer(7), null);
  assert.equal(room.chat_messages.length, before);
  assert.ok(toasts.includes('Phòng đã đầy'));
  app.currentUser = {id:2,name:'Guest'};
  context.fetch = async () => ({ok:true,json:async()=>({joined:false,actor_user_id:'1',room:{id:7,players:[{id:1,name:'Host'}]}})});
  assert.equal(await app.joinRoomOnServer(7),null);
  context.window.BadmintonSession = { headers:()=>({'X-Tab-Session':'test-tab-locator-2'}), user:()=>null };
  context.fetch = async (url, options) => {
    assert.equal(options.headers['X-Tab-Session'],'test-tab-locator-2');
    return {ok:true,json:async()=>({joined:true,actor_user_id:'2',room:{id:7,room_number:3,players:[{id:1,name:'Host'},{id:2,name:'Guest'}],current_players:2,max_players:2,status:'MATCHED'}})};
  };
  const joined = await app.joinRoomOnServer(7);
  assert.equal(joined.players.length,2);
  assert.ok(app.isRoomMember(joined));
  const elements = {};
  for (const id of ['room-detail-title','room-detail-status-badge','btn-join-room-action']) elements[id]={style:{}};
  context.document.getElementById = id => elements[id] || null;
  app.currentUser={id:1,name:'Host'};
  app.activeRoom={id:7,room_number:3,players:[{id:1,name:'Host'}],max_players:2,current_players:1,status:'OPEN'};
  app.currentView='ui-07';
  app.renderActiveRoomHeader();
  assert.ok(elements['room-detail-status-badge'].innerHTML.includes('1/2'));
  app.renderRoomDetailMembers=()=>{};
  app.renderChatMessages=()=>{};
  app.renderAIRoomTactics=()=>{};
  context.MockData.matchmaking_rooms=[joined];
  app.handleLiveSyncEvent({type:'CENTRAL_DATABASE_UPDATED'});
  assert.ok(elements['room-detail-status-badge'].innerHTML.includes('2/2'));
  assert.ok(elements['btn-join-room-action'].innerHTML.includes('Bạn Đã Trong Kèo'));
  context.TestApp.prototype.init = () => {};
  listeners.DOMContentLoaded();
  assert.ok(context.window.app instanceof context.TestApp);
  console.log('Room UI: recipient filtering, background/unread, deduplication, escaping, failed send/retry and join failure passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
