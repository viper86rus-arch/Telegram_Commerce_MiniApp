/**
 * ==============================================================================
 * Telegram_Commerce_MiniApp: Frontend Client Logic & WebApp SDK Controller
 * ==============================================================================
 * Автор: V1PER (viper86rus-arch)
 * GitHub: https://github.com/viper86rus-arch/Telegram_Commerce_MiniApp
 * Лицензия: MIT License (2026)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
  // ============================================================================
  // 1. ИНИЦИАЛИЗАЦИЯ TELEGRAM WEBAPP SDK (ИЛИ BROWSER MOCK)
  // ============================================================================
  const tg = window.Telegram?.WebApp || {
    ready: () => console.log('[Mock WebApp] ready'),
    expand: () => console.log('[Mock WebApp] expand'),
    enableClosingConfirmation: () => {},
    close: () => console.log('[Mock WebApp] close'),
    sendData: (data) => console.log('[Mock WebApp] sendData:', data),
    HapticFeedback: {
      impactOccurred: (style) => console.log('[Mock Haptic]', style),
      notificationOccurred: (type) => console.log('[Mock Notification]', type)
    },
    MainButton: {
      text: '',
      color: '#22c55e',
      textColor: '#ffffff',
      isVisible: false,
      isActive: true,
      setText: function(t) { this.text = t; },
      show: function() { this.isVisible = true; },
      hide: function() { this.isVisible = false; },
      onClick: function(fn) { this._handler = fn; }
    },
    initDataUnsafe: { user: { first_name: 'V1PER Demo User', id: 10001 } }
  };

  try {
    tg.ready();
    tg.expand();
    tg.enableClosingConfirmation();
  } catch (e) {
    console.warn('Telegram SDK initialization note:', e);
  }

  // ============================================================================
  // 2. ГЛОБАЛЬНОЕ СОСТОЯНИЕ (STATE)
  // ============================================================================
  const state = {
    categories: [],
    products: [],
    activeCategory: 'all',
    searchQuery: '',
    cart: JSON.parse(localStorage.getItem('v1_cart') || '{}'),
    selectedProduct: null
  };

  // Элементы DOM
  const elements = {
    categoriesList: document.getElementById('categoriesList'),
    productsGrid: document.getElementById('productsGrid'),
    productsCount: document.getElementById('productsCount'),
    currentCategoryTitle: document.getElementById('currentCategoryTitle'),
    searchInput: document.getElementById('searchInput'),
    clearSearchBtn: document.getElementById('clearSearchBtn'),
    cartBtn: document.getElementById('cartBtn'),
    cartBadge: document.getElementById('cartBadge'),
    floatingCartBar: document.getElementById('floatingCartBar'),
    floatingCartCount: document.getElementById('floatingCartCount'),
    floatingCartTotal: document.getElementById('floatingCartTotal'),
    floatingCheckoutBtn: document.getElementById('floatingCheckoutBtn'),
    cartModal: document.getElementById('cartModal'),
    cartItemsList: document.getElementById('cartItemsList'),
    cartSubtotal: document.getElementById('cartSubtotal'),
    cartFinalTotal: document.getElementById('cartFinalTotal'),
    closeCartBtn: document.getElementById('closeCartBtn'),
    proceedToCheckoutBtn: document.getElementById('proceedToCheckoutBtn'),
    checkoutModal: document.getElementById('checkoutModal'),
    closeCheckoutBtn: document.getElementById('closeCheckoutBtn'),
    checkoutForm: document.getElementById('checkoutForm'),
    successModal: document.getElementById('successModal'),
    successOrderNum: document.getElementById('successOrderNum'),
    successCloseBtn: document.getElementById('successCloseBtn'),
    productDetailModal: document.getElementById('productDetailModal'),
    closeDetailBtn: document.getElementById('closeDetailBtn'),
    detailImg: document.getElementById('detailImg'),
    detailBadge: document.getElementById('detailBadge'),
    detailName: document.getElementById('detailName'),
    detailPrice: document.getElementById('detailPrice'),
    detailOldPrice: document.getElementById('detailOldPrice'),
    detailDesc: document.getElementById('detailDesc'),
    detailAddToCartBtn: document.getElementById('detailAddToCartBtn')
  };

  // ============================================================================
  // 3. ЗАГРУЗКА ДАННЫХ ИЗ REST API (С OFFLINE FALLBACK)
  // ============================================================================
  async function loadData() {
    try {
      const [catRes, prodRes] = await Promise.all([
        fetch('/api/categories').catch(() => null),
        fetch('/api/products').catch(() => null)
      ]);

      if (catRes && catRes.ok) {
        state.categories = await catRes.json();
      } else {
        state.categories = getFallbackCategories();
      }

      if (prodRes && prodRes.ok) {
        state.products = await prodRes.json();
      } else {
        state.products = getFallbackProducts();
      }
    } catch (err) {
      console.warn('API недоступен, загружен fallback каталог:', err);
      state.categories = getFallbackCategories();
      state.products = getFallbackProducts();
    }

    renderCategories();
    renderProducts();
    updateCartUI();
  }

  // ============================================================================
  // 4. РЕНДЕРИНГ КАТЕГОРИЙ И ТОВАРОВ
  // ============================================================================
  function renderCategories() {
    elements.categoriesList.innerHTML = '';
    state.categories.forEach(cat => {
      const pill = document.createElement('button');
      pill.className = `category-pill ${cat.id === state.activeCategory ? 'active' : ''}`;
      pill.innerHTML = `<span>${escapeHtml(cat.icon)}</span> <span>${escapeHtml(cat.name)}</span>`;
      pill.addEventListener('click', () => {
        tg.HapticFeedback?.impactOccurred('light');
        state.activeCategory = cat.id;
        document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        elements.currentCategoryTitle.textContent = cat.name;
        renderProducts();
      });
      elements.categoriesList.appendChild(pill);
    });
  }

  function renderProducts() {
    elements.productsGrid.innerHTML = '';

    const filtered = state.products.filter(p => {
      const matchesCat = state.activeCategory === 'all' || p.category_id === state.activeCategory;
      const matchesSearch = !state.searchQuery || 
        p.name.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
        p.description.toLowerCase().includes(state.searchQuery.toLowerCase());
      return matchesCat && matchesSearch;
    });

    elements.productsCount.textContent = `${filtered.length} товаров`;

    if (filtered.length === 0) {
      elements.productsGrid.innerHTML = `
        <div style="grid-column: span 2; text-align: center; padding: 40px 10px; color: var(--hint-color);">
          <div style="font-size: 32px; margin-bottom: 8px;">🔍</div>
          <div>Товары не найдены</div>
        </div>
      `;
      return;
    }

    filtered.forEach(p => {
      const card = document.createElement('div');
      card.className = 'product-card';
      const qtyInCart = state.cart[p.id] || 0;

      card.innerHTML = `
        <div class="product-img-box">
          <img src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.name)}" loading="lazy">
          ${p.badge ? `<span class="product-badge">${escapeHtml(p.badge)}</span>` : ''}
        </div>
        <div class="product-info">
          <div class="product-name">${escapeHtml(p.name)}</div>
          <div class="product-price-row">
            <span class="current-price">${formatPrice(p.price)}</span>
            ${p.old_price ? `<span class="old-price">${formatPrice(p.old_price)}</span>` : ''}
          </div>
          <div class="product-actions" id="action-box-${p.id}">
            ${renderActionButtonHtml(p.id, qtyInCart)}
          </div>
        </div>
      `;

      // Клик по карточке (кроме кнопок) открывает модалку деталей
      card.querySelector('.product-img-box').addEventListener('click', () => openProductDetail(p));
      card.querySelector('.product-name').addEventListener('click', () => openProductDetail(p));

      // Навешивание событий на кнопки корзины
      bindCardActionEvents(card, p);

      elements.productsGrid.appendChild(card);
    });
  }

  function renderActionButtonHtml(productId, qty) {
    const safeId = escapeHtml(productId);
    if (qty > 0) {
      return `
        <div class="qty-controls">
          <button class="qty-btn btn-dec" data-id="${safeId}">−</button>
          <span class="qty-value">${qty}</span>
          <button class="qty-btn btn-inc" data-id="${safeId}">+</button>
        </div>
      `;
    }
    return `
      <button class="add-btn btn-add" data-id="${safeId}">
        <span>В корзину</span>
      </button>
    `;
  }

  function bindCardActionEvents(cardElement, product) {
    const actionBox = cardElement.querySelector(`#action-box-${product.id}`);
    actionBox.addEventListener('click', (e) => {
      e.stopPropagation();
      const target = e.target.closest('button');
      if (!target) return;

      if (target.classList.contains('btn-add') || target.classList.contains('btn-inc')) {
        addToCart(product.id);
      } else if (target.classList.contains('btn-dec')) {
        removeFromCart(product.id);
      }
    });
  }

  // ============================================================================
  // 5. УПРАВЛЕНИЕ КОРЗИНОЙ (CART LOGIC)
  // ============================================================================
  function addToCart(productId) {
    tg.HapticFeedback?.impactOccurred('medium');
    state.cart[productId] = (state.cart[productId] || 0) + 1;
    saveCart();
    updateProductActionUI(productId);
    updateCartUI();
  }

  function removeFromCart(productId) {
    tg.HapticFeedback?.impactOccurred('light');
    if (state.cart[productId] > 1) {
      state.cart[productId]--;
    } else {
      delete state.cart[productId];
    }
    saveCart();
    updateProductActionUI(productId);
    updateCartUI();
  }

  function saveCart() {
    localStorage.setItem('v1_cart', JSON.stringify(state.cart));
  }

  function updateProductActionUI(productId) {
    const actionBox = document.getElementById(`action-box-${productId}`);
    if (actionBox) {
      const qty = state.cart[productId] || 0;
      actionBox.innerHTML = renderActionButtonHtml(productId, qty);
    }
  }

  function getCartSummary() {
    let count = 0;
    let total = 0;
    const items = [];

    for (const [id, qty] of Object.entries(state.cart)) {
      const product = state.products.find(p => p.id === id);
      if (product && qty > 0) {
        count += qty;
        const subtotal = product.price * qty;
        total += subtotal;
        items.push({ product, quantity: qty, subtotal });
      }
    }
    return { count, total, items };
  }

  function updateCartUI() {
    const { count, total, items } = getCartSummary();

    // Бейдж в шапке
    if (count > 0) {
      elements.cartBadge.textContent = count;
      elements.cartBadge.classList.add('active');
    } else {
      elements.cartBadge.classList.remove('active');
    }

    // Плавающий нижний бар
    if (count > 0 && !elements.cartModal.classList.contains('open') && !elements.checkoutModal.classList.contains('open')) {
      elements.floatingCartCount.textContent = count;
      elements.floatingCartTotal.textContent = formatPrice(total);
      elements.floatingCartBar.classList.add('visible');
    } else {
      elements.floatingCartBar.classList.remove('visible');
    }

    // Интеграция с Telegram MainButton
    if (count > 0) {
      tg.MainButton.setText(`Оформить заказ: ${formatPrice(total)}`);
      tg.MainButton.show();
    } else {
      tg.MainButton.hide();
    }

    // Обновление списка товаров в шторке корзины
    renderCartItems(items, total);
  }

  function renderCartItems(items, total) {
    elements.cartItemsList.innerHTML = '';
    elements.cartSubtotal.textContent = formatPrice(total);
    elements.cartFinalTotal.textContent = formatPrice(total);

    if (items.length === 0) {
      elements.cartItemsList.innerHTML = `
        <div style="text-align: center; padding: 40px 10px; color: var(--hint-color);">
          <div style="font-size: 32px; margin-bottom: 8px;">🛒</div>
          <div>Корзина пока пуста</div>
        </div>
      `;
      elements.proceedToCheckoutBtn.style.display = 'none';
      return;
    }

    elements.proceedToCheckoutBtn.style.display = 'block';

    items.forEach(({ product, quantity, subtotal }) => {
      const itemRow = document.createElement('div');
      itemRow.className = 'cart-item';
      const safeId = escapeHtml(product.id);
      itemRow.innerHTML = `
        <img class="cart-item-img" src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.name)}">
        <div class="cart-item-info">
          <div class="cart-item-name">${escapeHtml(product.name)}</div>
          <div class="cart-item-price">${formatPrice(subtotal)}</div>
        </div>
        <div class="qty-controls">
          <button class="qty-btn btn-cart-dec" data-id="${safeId}">−</button>
          <span class="qty-value">${quantity}</span>
          <button class="qty-btn btn-cart-inc" data-id="${safeId}">+</button>
        </div>
      `;

      itemRow.querySelector('.btn-cart-dec').addEventListener('click', () => removeFromCart(product.id));
      itemRow.querySelector('.btn-cart-inc').addEventListener('click', () => addToCart(product.id));

      elements.cartItemsList.appendChild(itemRow);
    });
  }

  // ============================================================================
  // 6. МОДАЛЬНЫЕ ОКНА И ОФОРМЛЕНИЕ ЗАКАЗА
  // ============================================================================
  function openCart() {
    tg.HapticFeedback?.impactOccurred('light');
    elements.cartModal.classList.add('open');
    elements.floatingCartBar.classList.remove('visible');
  }

  function closeCart() {
    elements.cartModal.classList.remove('open');
    updateCartUI();
  }

  function openCheckout() {
    closeCart();
    elements.checkoutModal.classList.add('open');
  }

  function closeCheckout() {
    elements.checkoutModal.classList.remove('open');
    updateCartUI();
  }

  function openProductDetail(product) {
    state.selectedProduct = product;
    elements.detailImg.src = product.image_url;
    elements.detailName.textContent = product.name;
    elements.detailPrice.textContent = formatPrice(product.price);
    elements.detailOldPrice.textContent = product.old_price ? formatPrice(product.old_price) : '';
    elements.detailDesc.textContent = product.description;
    if (product.badge) {
      elements.detailBadge.style.display = 'inline-block';
      elements.detailBadge.textContent = product.badge;
    } else {
      elements.detailBadge.style.display = 'none';
    }
    elements.productDetailModal.classList.add('open');
  }

  function closeProductDetail() {
    elements.productDetailModal.classList.remove('open');
    state.selectedProduct = null;
  }

  // ============================================================================
  // 7. ОБРАБОТЧИКИ СОБЫТИЙ
  // ============================================================================
  // Слушатель нативной кнопки Telegram MainButton
  tg.MainButton.onClick(() => {
    if (!elements.cartModal.classList.contains('open') && !elements.checkoutModal.classList.contains('open')) {
      openCart();
    } else if (elements.cartModal.classList.contains('open')) {
      openCheckout();
    }
  });

  elements.cartBtn.addEventListener('click', openCart);
  elements.floatingCheckoutBtn.addEventListener('click', openCart);
  elements.closeCartBtn.addEventListener('click', closeCart);
  elements.proceedToCheckoutBtn.addEventListener('click', openCheckout);
  elements.closeCheckoutBtn.addEventListener('click', closeCheckout);
  elements.closeDetailBtn.addEventListener('click', closeProductDetail);

  elements.detailAddToCartBtn.addEventListener('click', () => {
    if (state.selectedProduct) {
      addToCart(state.selectedProduct.id);
      closeProductDetail();
    }
  });

  // Выбор способа оплаты в форме
  document.querySelectorAll('.payment-method-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.payment-method-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      card.querySelector('input').checked = true;
    });
  });

  // Поиск товаров
  elements.searchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim();
    elements.clearSearchBtn.style.display = state.searchQuery ? 'block' : 'none';
    renderProducts();
  });

  elements.clearSearchBtn.addEventListener('click', () => {
    elements.searchInput.value = '';
    state.searchQuery = '';
    elements.clearSearchBtn.style.display = 'none';
    renderProducts();
  });

  // Отправка формы заказа
  elements.checkoutForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const { total, items } = getCartSummary();
    if (items.length === 0) return;

    const payload = {
      customer_name: document.getElementById('inputName').value.trim(),
      phone: document.getElementById('inputPhone').value.trim(),
      address: document.getElementById('inputAddress').value.trim(),
      payment_method: document.querySelector('input[name="paymentMethod"]:checked').value,
      items: items.map(i => ({ id: i.product.id, quantity: i.quantity })),
      notes: 'Заказ через Telegram Mini App'
    };

    try {
      const response = await fetch('/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      let result = null;
      if (response.ok) {
        result = await response.json();
      } else {
        result = { order_id: `ORD-2026-${Math.random().toString(36).substr(2, 6).toUpperCase()}` };
      }

      // Отправка данных нативному боту через WebApp SDK
      try {
        tg.sendData(JSON.stringify({
          action: 'order_created',
          order_id: result.order_id,
          total: total
        }));
      } catch (err) {
        console.log('sendData mock handled:', err);
      }

      // Очистка корзины и показ экрана успеха
      state.cart = {};
      saveCart();
      updateCartUI();
      closeCheckout();

      tg.HapticFeedback?.notificationOccurred('success');
      elements.successOrderNum.textContent = result.order_id;
      elements.successModal.classList.add('open');

    } catch (err) {
      console.error('Ошибка оформления заказа:', err);
      alert('Заказ зарегистрирован локально. Спасибо!');
      closeCheckout();
    }
  });

  elements.successCloseBtn.addEventListener('click', () => {
    elements.successModal.classList.remove('open');
    elements.checkoutForm.reset();
  });

  // Закрытие модалок по клику на оверлей
  [elements.cartModal, elements.checkoutModal, elements.productDetailModal, elements.successModal].forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('open');
        if (modal === elements.successModal) {
          elements.checkoutForm.reset();
        }
        updateCartUI();
      }
    });
  });

  // ============================================================================
  // 8. УТИЛИТЫ И FALLBACK ДАННЫЕ
  // ============================================================================
  function formatPrice(num) {
    return new Intl.NumberFormat('ru-RU').format(num) + ' ₽';
  }

  function escapeHtml(str) {
    return (str || '').replace(/[&<>"']/g, m => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m]);
  }

  function getFallbackCategories() {
    return [
      { id: 'all', name: 'Все решения', icon: '⚡' },
      { id: 'hardware', name: 'Серверы', icon: '🖥️' },
      { id: 'gadgets', name: 'Девайсы', icon: '📱' },
      { id: 'accessories', name: 'Аксессуары', icon: '🎧' }
    ];
  }

  function getFallbackProducts() {
    return [
      {
        id: 'p-101', category_id: 'hardware', name: 'Мини-сервер CyberNode X1',
        description: '8 ядер, 32GB RAM, 1TB NVMe, бесшумное пассивное охлаждение.',
        price: 48900, old_price: 56000, badge: 'Хит',
        image_url: 'img/p101_server.svg'
      },
      {
        id: 'p-103', category_id: 'gadgets', name: 'Механическая клавиатура Stealth 75',
        description: 'Кастомная алюминиевая клавиатура с тактильными тихими свитчами.',
        price: 12900, old_price: 15500, badge: 'Новинка',
        image_url: 'img/p103_keyboard.svg'
      },
      {
        id: 'p-104', category_id: 'accessories', name: 'Магнитная док-станция Matrix 3-in-1',
        description: 'Быстрая зарядка 25W для смартфона, часов и наушников.',
        price: 5900, old_price: 7200, badge: '-18%',
        image_url: 'img/p104_dock.svg'
      }
    ];
  }

  // Старт приложения
  loadData();
});
