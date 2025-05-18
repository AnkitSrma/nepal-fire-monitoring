document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('map-modal');
  const modalImage = document.getElementById('modal-image');
  const closeModal = () => modal.classList.add('hidden');

  document.getElementById('modal-close').addEventListener('click', closeModal);
  modal.addEventListener('click', e => {
    if (e.target === modal) closeModal();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) closeModal();
  });

  fetch('data/today.json')
    .then(res => res.json())
    .then(data => {
      // Header timestamp
      document.getElementById('last-updated').textContent = `Last updated: ${data.last_updated}`;

      // Map panel
      document.getElementById('map-image').src = data.map_url;
      document.getElementById('map-date').textContent = data.date;
      document.getElementById('download-map').href = data.map_url;
      document.getElementById('view-larger').addEventListener('click', () => {
        modalImage.src = data.map_url;
        modal.classList.remove('hidden');
      });

      // Stats
      document.getElementById('total-fires').textContent = data.stats.total_fires;
      document.getElementById('top-district').textContent = data.stats.top_district;
      document.getElementById('protected-count').textContent = data.stats.protected_areas;
      document.getElementById('satellite').textContent = data.stats.satellite;
      document.getElementById('download-pdf').href = data.reports.pdf;
      document.getElementById('download-xlsx').href = data.reports.xlsx;

      // Archive
      const archive = data.archive;
      const months = [...new Set(archive.map(item => item.date.slice(5,7)))];
      const monthSelect = document.getElementById('month-select');
      months.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = new Date(`${data.year}-${m}-01`).toLocaleString('default',{ month: 'long' });
        monthSelect.appendChild(opt);
      });

      let currentPage = 0;
      const perPage = 9;
      const listEl = document.getElementById('archive-list');

      function renderPage(filtered) {
        listEl.innerHTML = '';
        const slice = filtered.slice(currentPage * perPage, (currentPage+1)*perPage);
        slice.forEach(item => {
          const card = document.createElement('div');
          card.className = 'bg-gray-50 rounded-lg shadow p-4 hover-scale transition';
          card.innerHTML = `
            <h3 class="font-semibold text-lg text-gray-800 mb-2">${item.district} - ${item.date}</h3>
            <img src="${item.map_url}" alt="Map ${item.date}" class="w-full rounded mb-2 fade-in" />
            <div class="flex space-x-2">
              <a href="${item.pdf}" download class="flex-1 px-3 py-1 bg-nepal-blue text-white rounded text-sm hover-scale">PDF</a>
              <a href="${item.xlsx}" download class="flex-1 px-3 py-1 bg-fire-accent text-white rounded text-sm hover-scale">XLSX</a>
            </div>
          `;
          listEl.appendChild(card);
        });
      }

      function applyFilter() {
        const query = document.getElementById('search-input').value.toLowerCase();
        const monthVal = document.getElementById('month-select').value;
        const filtered = archive.filter(item => {
          const matchQuery = !query || item.district.toLowerCase().includes(query) || item.date.includes(query);
          const matchMonth = !monthVal || item.date.slice(5,7) === monthVal;
          return matchQuery && matchMonth;
        });
        currentPage = 0;
        renderPage(filtered);
        document.getElementById('load-more-btn').onclick = () => {
          currentPage++;
          renderPage(filtered);
        };
      }

      document.getElementById('filter-btn').addEventListener('click', applyFilter);
      applyFilter();
    })
    .catch(err => console.error('Error loading data:', err));
});