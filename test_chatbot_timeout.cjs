const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let fireTimeout, cleared = false;
const context = vm.createContext({
  console: { warn() {} }, AbortController, Date, Math,
  window: {}, localStorage: { getItem() {} }, sessionStorage: { getItem() {} },
  setTimeout(callback, ms) { assert.equal(ms, 25000); fireTimeout = callback; return 1; },
  clearTimeout(id) { assert.equal(id, 1); cleared = true; },
  fetch(url, options) {
    return new Promise((resolve, reject) => {
      options.signal.addEventListener('abort', () => {
        const error = new Error('timeout'); error.name = 'AbortError'; reject(error);
      });
    });
  },
});
const source = fs.readFileSync('js/chatbot.js', 'utf8').split('// Instantiate global chatbot instance')[0];
vm.runInContext(source + '\nglobalThis.Chatbot = BadmintonAIChatbot;', context);
const bot = Object.create(context.Chatbot.prototype);
Object.assign(bot, { messages: [], isProcessing: false, apiEndpoint: '/api/chat' });
for (const name of ['saveHistory', 'renderMessages', 'showTypingIndicator']) bot[name] = () => {};
let typingRemoved = false, sendEnabled = false;
bot.removeTypingIndicator = () => { typingRemoved = true; };
bot.setSendButtonState = value => { sendEnabled = value; };
(async () => {
  const pending = bot.sendMessage('Sáng');
  assert.equal(bot.isProcessing, true);
  fireTimeout();
  await pending;
  assert.equal(bot.isProcessing, false);
  assert.equal(sendEnabled, true);
  assert.equal(typingRemoved, true);
  assert.equal(cleared, true);
  assert.match(bot.messages.at(-1).text, /quá nhiều thời gian/);
  console.log('Chat timeout releases typing indicator and send button: OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
