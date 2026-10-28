const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const events = [], writes = [];
let snapshot = { users: [{ id: 1, name: 'Host' }], facilities: [], matchmaking_rooms: [], notifications: [] };
const ctx = vm.createContext({
  console, setInterval() {},
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  window: { addEventListener() {}, app: { handleLiveSyncEvent(event) { events.push(event); } } },
  fetch: async (url, options) => {
    if (options?.method === 'POST') {
      writes.push(JSON.parse(options.body));
      return { ok: true, json: async () => ({ room_numbers: { '7': 3 } }) };
    }
    return { ok: true, json: async () => JSON.parse(JSON.stringify(snapshot)) };
  },
});
vm.runInContext(fs.readFileSync('js/data.js', 'utf8'), ctx);
(async () => {
  await vm.runInContext('fetchCentralServerDatabase()', ctx);
  snapshot.notifications = [{ id: 'n1', type: 'ROOM_MEMBER_JOINED', recipient_id: 1, sender_name: 'Player 2', room_id: 7 }];
  await vm.runInContext('fetchCentralServerDatabase()', ctx);
  snapshot.notifications.push({ id: 'n2', type: 'ROOM_CHAT_MESSAGE', recipient_id: 1, sender_name: 'Player 2', room_id: 7 });
  await vm.runInContext('fetchCentralServerDatabase()', ctx);
  await vm.runInContext('fetchCentralServerDatabase()', ctx);
  const roomEvents = events.filter(e => e.type === 'ROOM_NOTIFICATION');
  assert.deepEqual(roomEvents.map(e => e.payload.notification.id), ['n1', 'n2']);
  // Unconfirmed chat rows must never be uploaded via a generic snapshot save.
  await vm.runInContext(`syncDataToCentralServer({ matchmaking_rooms: [{ id: 7, chat_messages: [
    { id: 'sent', delivery_state: 'sent' }, { id: 'pending', delivery_state: 'pending' }, { id: 'failed', delivery_state: 'failed' }
  ] }] })`, ctx);
  assert.deepEqual(writes[0].matchmaking_rooms[0].chat_messages.map(m => m.id), ['sent']);
  vm.runInContext(`MockData.matchmaking_rooms = [{ id: 7, chat_messages: [{ id: 'retry', delivery_state: 'failed' }] }];
    applyDataToMockData({ matchmaking_rooms: [{ id: 7, chat_messages: [] }] });`, ctx);
  assert.equal(vm.runInContext('MockData.matchmaking_rooms[0].chat_messages[0].id', ctx), 'retry');
  console.log('Room sync: cross-browser join/chat dispatch once, failed/pending messages excluded from snapshots: OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
