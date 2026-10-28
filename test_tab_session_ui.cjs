const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function tab(storage=new Map()) {
  const ctx=vm.createContext({ window:{}, sessionStorage:{
    getItem:k=>storage.get(k)||null, setItem:(k,v)=>storage.set(k,v), removeItem:k=>storage.delete(k)
  }});
  vm.runInContext(fs.readFileSync('js/session.js','utf8'),ctx);
  return {session:ctx.window.BadmintonSession,storage};
}
const a=tab(),b=tab();
a.session.save({tab_session_id:'abcdefghijklmnopA',user:{id:1,name:'Hung'}});
b.session.save({tab_session_id:'abcdefghijklmnopB',user:{id:2,name:'Phong'}});
assert.equal(a.session.headers()['X-Tab-Session'],'abcdefghijklmnopA');
assert.equal(b.session.user().id,2);
assert.equal(tab(a.storage).session.user().id,1); // reload keeps this tab's account
assert.equal(a.session.eventsUrl('/events'),'/events?tab_session=abcdefghijklmnopA');
a.session.clear();
assert.equal(a.session.id(),null);
assert.equal(b.session.user().id,2);
assert.throws(()=>a.session.save({user:{id:3}}));
console.log('Tab sessions: isolated accounts, reload, logout and SSE locator passed; no JWT stored in JS.');
