let currentType = '';

// تحميل رسائل التليكرام
function loadTelegramMessages() {
    fetch('/get_messages/telegram')
    .then(response => response.json())
    .then(data => {
        let box = document.getElementById('telegramBox');
        box.innerHTML = '';
        data.forEach(msg => {
            let div = document.createElement('div');
            div.className = 'message';
            div.innerHTML = `<b>${msg[0]}</b>: ${msg[1]} <br><small>${msg[2]}</small>`;
            box.appendChild(div);
        });
    });
}

// تصفير رسائل التليكرام
function clearMessages(type) {
    if (type === 'telegram' && confirm("هل أنت متأكد أنك تريد تصفير الرسائل؟")) {
        fetch(`/clear_messages/${type}`, { method: 'POST' })
        .then(response => response.json())
        .then(() => {
            loadTelegramMessages();
        });
    }
}

// فتح نافذة إدارة قنوات التليكرام
function openChannelModal(type) {
    currentType = type;
    document.getElementById('modalTitle').innerText = 'قنوات التليكرام';
    const tbody = document.querySelector("#channelTable tbody");
    tbody.innerHTML = "";

    fetch(`/get_channels/${type}`)
    .then(response => response.json())
    .then(channels => {
        channels.forEach(line => {
            let parts = line.split('|');
            if (parts.length === 2) {
                addRow(parts[0].trim(), parts[1].trim());
            }
        });
        document.getElementById('modal').style.display = 'block';
    });
}

// إغلاق المودال
function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

// إضافة صف للقناة
function addRow(url = '', name = '') {
    const tbody = document.querySelector("#channelTable tbody");
    const tr = document.createElement("tr");
    tr.innerHTML = `
        <td><input type="text" value="${name}" placeholder="اسم القناة"></td>
        <td><input type="text" value="${url}" placeholder="الرابط"></td>
        <td><button onclick="deleteRow(this)">❌</button></td>
    `;
    tbody.appendChild(tr);
}

// حذف صف
function deleteRow(btn) {
    btn.closest("tr").remove();
}

// حفظ القنوات
function saveChannels() {
    const rows = document.querySelectorAll("#channelTable tbody tr");
    const channels = [];

    rows.forEach(row => {
        const url = row.cells[0].querySelector("input").value.trim();
        const name = row.cells[1].querySelector("input").value.trim();
        if (name && url) {
            channels.push(`${url} | ${name}`);
        }
    });

    fetch(`/save_channels/${currentType}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channels: channels })
    })
    .then(response => response.json())
    .then(() => {
        closeModal();
        loadChannelsTable(currentType);
    });
}

// تحميل جدول قنوات التليكرام
function loadChannelsTable(type) {
    fetch(`/get_channels/${type}`)
    .then(response => response.json())
    .then(channels => {
        const tableId = '#telegramTable';

        if ($.fn.dataTable.isDataTable(tableId)) {
            $(tableId).DataTable().destroy();
        }

        $(tableId).DataTable({
            data: channels.map(ch => {
                let parts = ch.split('|');
                let url = parts.length >= 1 ? parts[0].trim() : 'رابط غير معروف';
                let name = parts.length >= 2 ? parts[1].trim() : 'اسم غير معروف';
                return [
                    url,
                    `<a href="${url}" target="_blank">${name}</a>`
                ];
            }),
            columns: [
                { title: " الرابط " },
                 { title: " اسم القناة " }   
               
            ],
            language: {
                search: "بحث:",
                lengthMenu: "عرض _MENU_ قناة",
                info: "عرض _START_ إلى _END_ من _TOTAL_ قناة",
                paginate: {
                    first: "الأول",
                    last: "الأخير",
                    next: "التالي",
                    previous: "السابق"
                }
            }
        });
    });
}

// تحميل رسائل التليكرام بشكل دوري
setInterval(loadTelegramMessages, 3000);

// تحميل جدول القنوات عند البداية
loadChannelsTable('telegram');
