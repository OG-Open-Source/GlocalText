document.addEventListener('DOMContentLoaded', () => {
	// Mobile Menu Toggle
	const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
	const navLinks = document.querySelector('.nav-links');

	if (mobileMenuBtn) {
		mobileMenuBtn.addEventListener('click', () => {
			navLinks.classList.toggle('active');
			mobileMenuBtn.classList.toggle('active');
		});
	}

	// Search Functionality (for docs.html)
	const searchInput = document.getElementById('docs-search');
	const searchResultsContainer = document.getElementById('search-results');
	const docSections = document.querySelectorAll('.doc-section');

	if (searchInput) {
		searchInput.addEventListener('input', (e) => {
			const query = e.target.value.toLowerCase();

			if (query.length < 2) {
				searchResultsContainer.classList.remove('active');
				return;
			}

			const results = [];
			docSections.forEach((section) => {
				const title = section.querySelector('h2, h3').innerText;
				const content = section.innerText;

				if (content.toLowerCase().includes(query)) {
					results.push({
						id: section.id,
						title: title,
						preview: getPreview(content, query),
					});
				}
			});

			displayResults(results);
		});

		// Hide results when clicking outside
		document.addEventListener('click', (e) => {
			if (!searchInput.contains(e.target) && !searchResultsContainer.contains(e.target)) {
				searchResultsContainer.classList.remove('active');
			}
		});
	}

	function getPreview(content, query) {
		const index = content.toLowerCase().indexOf(query);
		const start = Math.max(0, index - 20);
		const end = Math.min(content.length, index + query.length + 20);
		return '...' + content.substring(start, end) + '...';
	}

	function displayResults(results) {
		searchResultsContainer.innerHTML = '';

		if (results.length === 0) {
			searchResultsContainer.innerHTML = '<div class="no-results">No results found</div>';
		} else {
			results.forEach((result) => {
				const div = document.createElement('div');
				div.className = 'search-result-item';
				div.innerHTML = `
                    <div class="result-title">${result.title}</div>
                    <div class="result-preview">${result.preview}</div>
                `;
				div.addEventListener('click', () => {
					document.getElementById(result.id).scrollIntoView({ behavior: 'smooth' });
					searchResultsContainer.classList.remove('active');
					searchInput.value = '';
				});
				searchResultsContainer.appendChild(div);
			});
		}

		searchResultsContainer.classList.add('active');
	}

	// Theme Toggle
	const themeToggleBtn = document.getElementById('theme-toggle');
	const htmlElement = document.documentElement;

	// Check for saved user preference, if any, on load of the website
	const savedTheme = localStorage.getItem('theme');
	const systemTheme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';

	if (savedTheme) {
		htmlElement.setAttribute('data-theme', savedTheme);
		updateThemeIcon(savedTheme);
	} else if (systemTheme === 'light') {
		htmlElement.setAttribute('data-theme', 'light');
		updateThemeIcon('light');
	}

	if (themeToggleBtn) {
		themeToggleBtn.addEventListener('click', () => {
			const currentTheme = htmlElement.getAttribute('data-theme');
			const newTheme = currentTheme === 'light' ? 'dark' : 'light';

			htmlElement.setAttribute('data-theme', newTheme);
			localStorage.setItem('theme', newTheme);
			updateThemeIcon(newTheme);
		});
	}

	function updateThemeIcon(theme) {
		if (themeToggleBtn) {
			themeToggleBtn.textContent = theme === 'light' ? '🌙' : '☀️';
		}
	}
});
