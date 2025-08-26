async function load() {
  const res = await fetch('/api/data');
  const data = await res.json();
  const container = document.getElementById('content');
  container.innerHTML = '';
  Object.entries(data).forEach(([cat, items]) => {
    const h = document.createElement('h2');
    h.textContent = cat;
    container.appendChild(h);

    const list = document.createElement('ul');
    items.forEach(item => {
      const li = document.createElement('li');
      li.innerHTML = `<a href="${item.url}" target="_blank">${item.name}</a>`;
      const del = document.createElement('button');
      del.textContent = 'Delete';
      del.onclick = () => deleteItem(cat, item.name);
      li.appendChild(del);
      list.appendChild(li);
    });
    container.appendChild(list);

    const nameInput = document.createElement('input');
    nameInput.placeholder = 'Name';
    const urlInput = document.createElement('input');
    urlInput.placeholder = 'URL';
    const addBtn = document.createElement('button');
    addBtn.textContent = 'Add';
    addBtn.onclick = () => addItem(cat, nameInput.value, urlInput.value);
    container.appendChild(nameInput);
    container.appendChild(urlInput);
    container.appendChild(addBtn);

    const delCatBtn = document.createElement('button');
    delCatBtn.textContent = 'Delete Category';
    delCatBtn.onclick = () => deleteCategory(cat);
    container.appendChild(delCatBtn);
  });
}

async function addCategory() {
  const name = document.getElementById('new-cat').value;
  await fetch('/api/add_category', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name})});
  document.getElementById('new-cat').value='';
  load();
}

async function deleteCategory(name) {
  await fetch('/api/delete_category', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name})});
  load();
}

async function addItem(category, name, url) {
  await fetch('/api/add_item', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({category, name, url})});
  load();
}

async function deleteItem(category, name) {
  await fetch('/api/delete_item', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({category, name})});
  load();
}

window.onload = load;
