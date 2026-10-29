const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map();
for (const id of ['booking-date-picker','facility-detail-name','facility-detail-address','slot-matrix-grid','equipment-rent-container','ai-chat-messages-body']) {
  elements.set(id, { value: '2026-10-29', innerHTML: '', scrollIntoView() { this.scrolled = true; } });
}
const context = vm.createContext({
  console, Date, Set, Math,
  document: { getElementById: id => elements.get(id), addEventListener() {} }, window: {},
  MockData: { facilities: [{id: 2, name: 'Hà Đông', address: 'Hà Nội'}], equipments: [
    {id:1, facility_id:2, name:'Vợt đúng cơ sở', price:20000, unit:'giờ'},
    {id:2, facility_id:3, name:'Vợt khác cơ sở', price:30000, unit:'giờ'},
  ] },
});
vm.runInContext(fs.readFileSync('js/app.js','utf8') + '\nglobalThis.App = BadmintonAIApp;', context);
const app = Object.create(context.App.prototype);
Object.assign(app, { selectedFacility:{id:1}, selectedSlots:[{id:9}], selectedEquipments:{1:2} });
for (const method of ['renderSlotMatrix','updateBookingSummary','showToast']) app[method] = () => {};
app.navigateTo = view => { app.currentView = view; };
context.testApp = app;
vm.runInContext('app = globalThis.testApp;', context);
assert.equal(app.openBookingFromChat({facility_id:2,date:'2026-11-01',section:'equipment'}), true);
assert.equal(app.selectedFacility.id, 2);
assert.equal(app.currentView, 'ui-03');
assert.equal(elements.get('booking-date-picker').value, '2026-11-01');
assert.equal(elements.get('equipment-rent-container').scrolled, true);
assert.equal(app.selectedSlots.length, 0);
assert.match(elements.get('equipment-rent-container').innerHTML, /Vợt đúng cơ sở/);
assert.doesNotMatch(elements.get('equipment-rent-container').innerHTML, /Vợt khác cơ sở/);
assert.equal(app.openBookingFromChat({facility_id:999}), false);
const source = fs.readFileSync('js/chatbot.js','utf8').split('// Instantiate global chatbot instance')[0];
vm.runInContext(source + '\nglobalThis.Chatbot = BadmintonAIChatbot;', context);
const bot = Object.create(context.Chatbot.prototype);
bot.messages = [{sender:'bot',text:'Sân còn trống',actions:[{type:'open_booking',facility_id:2,date:'2026-11-01',section:'schedule',label:'Mở lịch <script>'}]}];
bot.scrollToBottom = () => {};
bot.renderMessages();
assert.match(elements.get('ai-chat-messages-body').innerHTML, /openBookingAction\(0,0\)/);
assert.doesNotMatch(elements.get('ai-chat-messages-body').innerHTML, /<script>/);
let closed = false;
bot.toggle = value => { closed = value === false; };
bot.openBookingAction(0,0);
assert.equal(closed, true);
assert.equal(elements.get('slot-matrix-grid').scrolled, true);
console.log('Chat booking and equipment destinations: OK');
