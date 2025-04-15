/**
 * Améliorations dynamiques pour l'interface Anecoop
 * Ce script ajoute des fonctionnalités interactives pour améliorer l'expérience utilisateur
 */

// Gestion améliorée du chargement des ressources
document.addEventListener('DOMContentLoaded', function() {
  // Vérifier et charger dynamiquement les ressources manquantes
  const requiredLibraries = [
    { 
        name: 'FullCalendar', 
        check: () => typeof FullCalendar !== 'undefined',
        url: 'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.9/index.global.min.js',
        type: 'script' 
    },
    // Autres bibliothèques...
];

function showFallbackNotification(libraryName) {
    const notification = document.createElement('div');
    notification.className = 'fallback-notification';
    notification.innerHTML = `
        <div class="alert alert-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Fonctionnalité limitée</strong>
            <p>La bibliothèque ${libraryName} n'a pas pu être chargée. Certaines fonctionnalités peuvent être indisponibles.</p>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Disparition automatique après 5 secondes
    setTimeout(() => {
        document.body.removeChild(notification);
    }, 5000);
} 

function loadResource(resource) {
    return new Promise((resolve, reject) => {
        let element;
        
        if (resource.type === 'script') {
            element = document.createElement('script');
            element.src = resource.url;
            element.type = 'application/javascript';
            element.async = false;  // Chargement synchrone
            element.crossOrigin = 'anonymous';
        }
        
        element.onload = () => {
            console.log(`${resource.name} chargé avec succès`);
            resolve(true);
        };
        
        element.onerror = (error) => {
            console.error(`Échec du chargement de ${resource.name}`, error);
            // Afficher un message d'erreur à l'utilisateur
            showFallbackNotification(resource.name);
            resolve(false);
        };
        
        document.head.appendChild(element);
    });
}

  // Vérifier et charger les bibliothèques manquantes
  requiredLibraries.forEach(lib => {
    if (!lib.check()) {
      console.log(`Chargement dynamique de ${lib.name}...`);
      loadResource(lib).then(success => {
        if (success) {
          console.log(`${lib.name} chargé avec succès`);
          // Réinitialiser les fonctionnalités qui dépendent de cette bibliothèque
          if (lib.name === 'FullCalendar' && window.initCalendar) {
            window.initCalendar();
          }
        } else {
          // Fournir une alternative ou une notification en cas d'échec
          showFallbackNotification(lib.name);
        }
      });
    }
  });
  
  // Amélioration de la navigation par étapes
  enhanceStepNavigation();
  
  // Initialisation des interfaces dynamiques
  initDynamicUI();
  
  // Ajouter l'observateur d'intersection pour les animations au scroll
  setupScrollAnimations();
});

/**
 * Améliore la navigation par étapes avec des animations et validations
 */
function enhanceStepNavigation() {
  const steps = document.querySelectorAll('.step');
  if (!steps.length) return;
  
  // Ajouter des effets de transition entre les étapes
  steps.forEach((step, index) => {
    // Ajouter des infobulles explicatives
    const stepNumber = step.querySelector('.step-number');
    const stepTitle = step.querySelector('.step-title').textContent;
    
    if (stepNumber) {
      // Permettre à l'utilisateur de cliquer sur une étape précédente pour y revenir
      if (step.classList.contains('completed')) {
        step.style.cursor = 'pointer';
        step.addEventListener('click', function() {
          const stepId = this.id;
          // Extraire le numéro d'étape et rediriger vers la page correspondante
          const stepNum = stepId.replace('step', '');
          navigateToStep(stepNum);
        });
      }
      
      // Créer un tooltip détaillé pour chaque étape
      const tooltip = document.createElement('div');
      tooltip.className = 'step-tooltip';
      tooltip.innerHTML = `
        <strong>${stepTitle}</strong>
        <p>${getStepDescription(index + 1)}</p>
      `;
      
      // Afficher/masquer le tooltip au survol
      step.addEventListener('mouseenter', () => {
        step.appendChild(tooltip);
        setTimeout(() => tooltip.classList.add('visible'), 10);
      });
      
      step.addEventListener('mouseleave', () => {
        tooltip.classList.remove('visible');
        setTimeout(() => {
          if (tooltip.parentNode === step) {
            step.removeChild(tooltip);
          }
        }, 300);
      });
    }
  });
  
  // Animer la progression
  animateProgress();
}

/**
 * Retourne une description détaillée pour chaque étape
 */
function getStepDescription(stepNumber) {
  switch (stepNumber) {
    case 1:
      return "Sélectionnez votre département et indiquez vos coordonnées en tant que responsable.";
    case 2:
      return "Choisissez les modules de formation et les créneaux horaires disponibles.";
    case 3:
      return "Ajoutez entre 8 et 12 participants qui assisteront à la formation.";
    case 4:
      return "Téléchargez des documents ou sélectionnez des ressources existantes.";
    case 5:
      return "Vérifiez les informations et confirmez votre réservation.";
    default:
      return "";
  }
}

/**
 * Navigation entre les étapes
 */
function navigateToStep(stepNumber) {
  const routes = {
    1: '/index',
    2: '/formations',
    3: '/participants',
    4: '/documents',
    5: '/confirmation'
  };

  // Conserver les paramètres de la requête actuelle
  const currentParams = new URLSearchParams(window.location.search);
  let paramsString = '';
  
  if (currentParams.toString()) {
    paramsString = '?' + currentParams.toString();
  }

  if (routes[stepNumber]) {
    window.location.href = routes[stepNumber] + paramsString;
  }
}

/**
 * Anime la barre de progression pour montrer l'avancement
 */
function animateProgress() {
  const progressBar = document.getElementById('formationProgressBar') || 
                       document.getElementById('participantsProgress');
  if (!progressBar) return;
  
  const currentValue = parseInt(progressBar.getAttribute('aria-valuenow') || '0');
  const targetValue = parseInt(progressBar.style.width) || 0;
  
  // Animation fluide
  if (currentValue !== targetValue) {
    let value = currentValue;
    const interval = setInterval(() => {
      if (value < targetValue) {
        value += 1;
      } else if (value > targetValue) {
        value -= 1;
      } else {
        clearInterval(interval);
        return;
      }
      
      progressBar.style.width = `${value}%`;
      progressBar.setAttribute('aria-valuenow', value);
      
      if (value === targetValue) {
        clearInterval(interval);
      }
    }, 20);
  }
}

/**
 * Initialise les éléments d'interface utilisateur dynamiques
 */
function initDynamicUI() {
  // Améliorer les formulaires avec validation en temps réel
  enhanceForms();
  
  // Ajouter des animations aux cartes d'information
  animateCards();
  
  // Améliorer les notifications
  enhanceNotifications();
  
  // Initialiser les filtres dynamiques pour les tableaux
  initDynamicFilters();
  
  // Améliorer le calendrier s'il existe
  enhanceCalendar();
  
  // Initialiser les tooltips
  initTooltips();
  
  // Remplacer les badges statiques par des badges dynamiques
  enhanceBadges();
}

/**
 * Améliore les formulaires avec validation en temps réel
 */
function enhanceForms() {
  const forms = document.querySelectorAll('form');
  
  forms.forEach(form => {
    const inputs = form.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
      // Validation en temps réel
      input.addEventListener('input', function() {
        validateInput(this);
      });
      
      // Validation au focus out
      input.addEventListener('blur', function() {
        validateInput(this, true);
      });
    });
    
    // Désactiver la soumission par défaut
    form.addEventListener('submit', function(e) {
      // Valider tous les champs avant soumission
      let isValid = true;
      
      inputs.forEach(input => {
        if (!validateInput(input, true)) {
          isValid = false;
        }
      });
      
      // Si le formulaire n'est pas valide, empêcher la soumission
      if (!isValid) {
        e.preventDefault();
        showFormError("Veuillez corriger les erreurs dans le formulaire avant de continuer.");
      } else {
        // Afficher un indicateur de chargement
        showLoadingIndicator(form);
      }
    });
  });
}

/**
 * Valide un champ de formulaire
 */
function validateInput(input, showError = false) {
  let isValid = true;
  let errorMessage = '';
  
  // Vérifier si le champ est requis
  if (input.hasAttribute('required') && !input.value.trim()) {
    isValid = false;
    errorMessage = 'Ce champ est requis';
  }
  
  // Validation spécifique selon le type
  switch (input.type) {
    case 'email':
      if (input.value && !isValidEmail(input.value)) {
        isValid = false;
        errorMessage = 'Adresse email invalide';
      }
      break;
    case 'tel':
      if (input.value && !isValidPhone(input.value)) {
        isValid = false;
        errorMessage = 'Numéro de téléphone invalide';
      }
      break;
    case 'date':
      if (input.value && !isValidDate(input.value)) {
        isValid = false;
        errorMessage = 'Date invalide';
      }
      break;
  }
  
  // Afficher/masquer l'erreur
  if (showError) {
    displayInputError(input, isValid ? '' : errorMessage);
  }
  
  // Ajouter/supprimer la classe de validation
  if (input.value.trim()) {
    input.classList.toggle('is-valid', isValid);
    input.classList.toggle('is-invalid', !isValid);
  } else {
    input.classList.remove('is-valid');
    input.classList.toggle('is-invalid', input.hasAttribute('required'));
  }
  
  return isValid;
}

/**
 * Affiche un message d'erreur pour un champ de formulaire
 */
function displayInputError(input, message) {
  // Chercher ou créer un élément pour afficher l'erreur
  let errorElement = input.nextElementSibling;
  
  if (!errorElement || !errorElement.classList.contains('input-error')) {
    errorElement = document.createElement('div');
    errorElement.className = 'input-error';
    input.parentNode.insertBefore(errorElement, input.nextSibling);
  }
  
  // Mettre à jour le message et l'affichage
  if (message) {
    errorElement.textContent = message;
    errorElement.style.display = 'block';
  } else {
    errorElement.style.display = 'none';
  }
}

/**
 * Animation des cartes d'information pour une interface plus dynamique
 */
function animateCards() {
  const cards = document.querySelectorAll('.card, .dashboard-card, .widget-container, .info-card');
  
  cards.forEach(card => {
    // Ajouter une classe pour l'animation au chargement
    card.classList.add('animate__animated', 'animate__fadeIn');
    
    // Observer l'intersection pour animer lors du scroll
    if ('IntersectionObserver' in window) {
      card.classList.add('animate-on-scroll');
    }
    
    // Ajouter une ombre au survol
    card.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-5px)';
      this.style.boxShadow = 'var(--shadow-lg)';
    });
    
    card.addEventListener('mouseleave', function() {
      this.style.transform = '';
      this.style.boxShadow = '';
    });
  });
}

/**
 * Configure les animations au défilement
 */
function setupScrollAnimations() {
  if (!('IntersectionObserver' in window)) return;
  
  const elements = document.querySelectorAll('.animate-on-scroll');
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, {
    rootMargin: '0px',
    threshold: 0.1
  });
  
  elements.forEach(element => {
    observer.observe(element);
  });
}

/**
 * Améliore le système de notifications
 */
function enhanceNotifications() {
  // Remplacement de la fonction showToast
  window.showToast = function(title, message, type = 'info') {
    // Déterminer la couleur selon le type
    let bgColor, icon;
    
    switch (type) {
      case 'success':
        bgColor = '#48bb78';
        icon = 'fas fa-check-circle';
        break;
      case 'warning':
        bgColor = '#f6ad55';
        icon = 'fas fa-exclamation-triangle';
        break;
      case 'error':
        bgColor = '#e53e3e';
        icon = 'fas fa-exclamation-circle';
        break;
      default: // info
        bgColor = '#63b3ed';
        icon = 'fas fa-info-circle';
        break;
    }
    
    // Si Toastify est disponible, l'utiliser
    if (typeof Toastify === 'function') {
      Toastify({
        text: `<i class="${icon}" style="margin-right: 8px;"></i><b>${title}</b><br>${message}`,
        duration: 4000,
        gravity: "bottom",
        position: "right",
        backgroundColor: bgColor,
        stopOnFocus: true,
        className: 'toast-notification',
        escapeMarkup: false,
        onClick: function() {}
      }).showToast();
    } else {
      // Fallback personnalisé si Toastify n'est pas disponible
      createCustomToast(title, message, type, icon);
    }
    
    // Ajouter également à la liste des notifications
    const notification = {
      title,
      message,
      type,
      timestamp: new Date().toISOString(),
      read: false
    };
    
    // Récupérer les notifications existantes
    const notifications = JSON.parse(localStorage.getItem('anecoop-notifications')) || [];
    
    // Ajouter la nouvelle notification au début
    notifications.unshift(notification);
    
    // Limiter à 50 notifications
    if (notifications.length > 50) {
      notifications.pop();
    }
    
    // Sauvegarder
    localStorage.setItem('anecoop-notifications', JSON.stringify(notifications));
    
    // Mettre à jour l'interface
    updateNotificationsUI();
  };
  
  // Mettre à jour l'affichage des notifications au chargement
  updateNotificationsUI();
}

/**
 * Met à jour l'interface des notifications
 */
function updateNotificationsUI() {
  const notificationsList = document.getElementById('notifications-list');
  const notificationsBadge = document.getElementById('notificationsBadge');
  
  if (!notificationsList || !notificationsBadge) return;
  
  // Récupérer les notifications depuis le localStorage
  const notifications = JSON.parse(localStorage.getItem('anecoop-notifications')) || [];
  
  // Mettre à jour le badge
  const unreadCount = notifications.filter(n => !n.read).length;
  if (unreadCount > 0) {
    notificationsBadge.textContent = unreadCount;
    notificationsBadge.classList.remove('hidden');
  } else {
    notificationsBadge.classList.add('hidden');
  }
  
  // Afficher les notifications
  if (notifications.length === 0) {
    notificationsList.innerHTML = '<div class="notification-item">Aucune notification</div>';
    return;
  }
  
  notificationsList.innerHTML = '';
  
  notifications.forEach((notification, index) => {
    const notificationEl = document.createElement('div');
    notificationEl.className = `notification-item${notification.read ? '' : ' unread'}`;
    
    // Formater la date
    const date = new Date(notification.timestamp);
    const formattedDate = `${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()} ${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
    
    // Icône selon le type
    let icon = 'info-circle';
    switch (notification.type) {
      case 'success': icon = 'check-circle'; break;
      case 'warning': icon = 'exclamation-triangle'; break;
      case 'error': icon = 'exclamation-circle'; break;
    }
    
    notificationEl.innerHTML = `
      <div><i class="fas fa-${icon}" style="color: var(--${notification.type || 'info'})"></i> <strong>${notification.title}</strong></div>
      <div>${notification.message}</div>
      <div class="notification-meta mt-2 d-flex justify-content-between">
        <small class="text-muted">${formattedDate}</small>
        <button class="btn btn-sm btn-link p-0 mark-read" data-index="${index}">
          ${notification.read ? 'Marquer comme non lu' : 'Marquer comme lu'}
        </button>
      </div>
    `;
    
    notificationsList.appendChild(notificationEl);
  });
  
  // Marquer comme lu/non lu
  document.querySelectorAll('.mark-read').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      const index = parseInt(this.dataset.index);
      markNotification(index);
    });
  });
}

/**
 * Marque une notification comme lue/non lue
 */
function markNotification(index) {
  const notifications = JSON.parse(localStorage.getItem('anecoop-notifications')) || [];
  
  if (index >= 0 && index < notifications.length) {
    notifications[index].read = !notifications[index].read;
    localStorage.setItem('anecoop-notifications', JSON.stringify(notifications));
    updateNotificationsUI();
  }
}

/**
 * Crée une notification toast personnalisée (fallback)
 */
function createCustomToast(title, message, type, icon) {
  // Créer le conteneur des toasts s'il n'existe pas
  let toastContainer = document.getElementById('custom-toast-container');
  
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'custom-toast-container';
    toastContainer.style.position = 'fixed';
    toastContainer.style.bottom = '20px';
    toastContainer.style.right = '20px';
    toastContainer.style.zIndex = '9999';
    document.body.appendChild(toastContainer);
  }
  
  // Créer le toast
  const toast = document.createElement('div');
  toast.className = `custom-toast toast-${type} animate__animated animate__fadeInUp`;
  toast.innerHTML = `
    <div class="toast-icon"><i class="${icon}"></i></div>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
    <button class="toast-close"><i class="fas fa-times"></i></button>
  `;
  
  // Ajouter au conteneur
  toastContainer.appendChild(toast);
  
  // Gérer la fermeture
  const closeBtn = toast.querySelector('.toast-close');
  closeBtn.addEventListener('click', () => {
    toast.classList.replace('animate__fadeInUp', 'animate__fadeOutDown');
    setTimeout(() => {
      if (toast.parentNode === toastContainer) {
        toastContainer.removeChild(toast);
      }
    }, 500);
  });
  
  // Auto-fermeture après 4 secondes
  setTimeout(() => {
    if (toast.parentNode === toastContainer) {
      toast.classList.replace('animate__fadeInUp', 'animate__fadeOutDown');
      setTimeout(() => {
        if (toast.parentNode === toastContainer) {
          toastContainer.removeChild(toast);
        }
      }, 500);
    }
  }, 4000);
}

/**
 * Initialise les filtres dynamiques pour les tableaux
 */
function initDynamicFilters() {
  const tables = document.querySelectorAll('table');
  
  tables.forEach(table => {
    // Vérifier si le tableau a un thead (pour éviter les tableaux de mise en page)
    if (!table.querySelector('thead')) return;
    
    // Ajouter la classe filterable
    table.classList.add('filterable');
    
    // Créer un conteneur de filtres au-dessus du tableau
    const filtersContainer = document.createElement('div');
    filtersContainer.className = 'table-filters';
    table.parentNode.insertBefore(filtersContainer, table);
    
    // Ajouter un champ de recherche global
    const searchContainer = document.createElement('div');
    searchContainer.className = 'search-filter';
    searchContainer.innerHTML = `
      <input type="text" class="form-control" placeholder="Rechercher...">
      <i class="fas fa-search"></i>
    `;
    filtersContainer.appendChild(searchContainer);
    
    // Ajouter des filtres pour chaque colonne avec des données
    const headers = table.querySelectorAll('thead th');
    
    headers.forEach((header, index) => {
      // Ajouter un attribut data-label pour la vue mobile
      const headerText = header.textContent.trim();
      
      table.querySelectorAll(`tbody tr td:nth-child(${index + 1})`).forEach(cell => {
        cell.setAttribute('data-label', headerText);
      });
      
      // Créer un filtre selon le contenu
      if (headerText && !header.classList.contains('no-filter')) {
        const colValues = new Set();
        table.querySelectorAll(`tbody tr td:nth-child(${index + 1})`).forEach(cell => {
          const value = cell.textContent.trim();
          if (value) colValues.add(value);
        });
        
        // Si la colonne a des valeurs distinctes et pas trop nombreuses
        if (colValues.size > 1 && colValues.size <= 15) {
          // Pour les dates, créer un filtre de plage de dates
          const hasDate = Array.from(colValues).some(val => isValidDate(val));
          
          if (hasDate) {
            const filterElement = createDateFilter(table, index, headerText);
            filtersContainer.appendChild(filterElement);
          } else {
            // Sinon, créer un filtre de sélection
            const filterElement = createSelectFilter(table, index, headerText, colValues);
            filtersContainer.appendChild(filterElement);
          }
        }
      }
    });
    
    // Ajouter la recherche globale
    const searchInput = searchContainer.querySelector('input');
    searchInput.addEventListener('input', function() {
      filterTable(table);
    });
  });
}

/**
 * Crée un filtre de sélection pour un tableau
 */
function createSelectFilter(table, columnIndex, filterName, values) {
  // Créer le select avec les options
  const container = document.createElement('div');
  container.className = 'select-filter';
  
  const select = document.createElement('select');
  select.className = 'form-control';
  select.setAttribute('data-column', columnIndex);
  
  // Option par défaut
  const defaultOption = document.createElement('option');
  defaultOption.value = '';
  defaultOption.textContent = `Filtrer par ${filterName}`;
  select.appendChild(defaultOption);
  
  // Ajouter toutes les options
  Array.from(values).sort().forEach(value => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
  
  container.appendChild(select);
  
  // Ajouter l'événement de changement
  select.addEventListener('change', function() {
    filterTable(table);
  });
  
  return container;
}

/**
 * Crée un filtre de plage de dates
 */
function createDateFilter(table, columnIndex, filterName) {
  const container = document.createElement('div');
  container.className = 'date-filter';
  
  container.innerHTML = `
    <label>${filterName}:</label>
    <div class="date-inputs">
      <input type="date" class="form-control" data-column="${columnIndex}" data-filter-type="date-start" placeholder="Date début">
      <span>à</span>
      <input type="date" class="form-control" data-column="${columnIndex}" data-filter-type="date-end" placeholder="Date fin">
    </div>
  `;
  
  // Ajouter les événements
  const inputs = container.querySelectorAll('input');
  inputs.forEach(input => {
    input.addEventListener('change', function() {
      filterTable(table);
    });
  });
  
  return container;
}

/**
 * Filtre un tableau selon les critères sélectionnés
 */
function filterTable(table) {
  const rows = table.querySelectorAll('tbody tr');
  const filters = table.parentNode.querySelectorAll('.table-filters [data-column]');
  const searchInput = table.parentNode.querySelector('.search-filter input');
  const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
  
  rows.forEach(row => {
    let showRow = true;
    
    // Vérifier la recherche globale
    if (searchTerm) {
      const rowText = row.textContent.toLowerCase();
      showRow = rowText.includes(searchTerm);
    }
    
    // Appliquer chaque filtre
    if (showRow) {
      filters.forEach(filter => {
        const columnIndex = parseInt(filter.getAttribute('data-column'));
        const cell = row.children[columnIndex];
        
        if (!cell) return;
        
        const cellValue = cell.textContent.trim();
        
        // Selon le type de filtre
        if (filter.tagName === 'SELECT') {
          // Filtre de sélection
          const filterValue = filter.value;
          if (filterValue && cellValue !== filterValue) {
            showRow = false;
          }
        } else if (filter.hasAttribute('data-filter-type')) {
          // Filtre de date
          const filterType = filter.getAttribute('data-filter-type');
          const filterValue = filter.value;
          
          if (filterValue) {
            const cellDate = parseDate(cellValue);
            const filterDate = new Date(filterValue);
            
            if (isNaN(cellDate.getTime())) {
              showRow = false;
            } else if (filterType === 'date-start' && cellDate < filterDate) {
              showRow = false;
            } else if (filterType === 'date-end' && cellDate > filterDate) {
              showRow = false;
            }
          }
        }
      });
    }
    
    // Afficher ou masquer la ligne
    row.style.display = showRow ? '' : 'none';
  });
  
  // Afficher un message si aucun résultat
  let noResultsRow = table.querySelector('tbody tr.no-results');
  
  if (Array.from(rows).every(row => row.style.display === 'none')) {
    if (!noResultsRow) {
      noResultsRow = document.createElement('tr');
      noResultsRow.className = 'no-results';
      const cell = document.createElement('td');
      cell.colSpan = table.querySelector('thead tr').children.length;
      cell.textContent = 'Aucun résultat trouvé';
      cell.style.textAlign = 'center';
      cell.style.padding = '20px';
      noResultsRow.appendChild(cell);
      table.querySelector('tbody').appendChild(noResultsRow);
    }
    noResultsRow.style.display = '';
  } else if (noResultsRow) {
    noResultsRow.style.display = 'none';
  }
}

/**
 * Améliore l'interface du calendrier
 */
function enhanceCalendar() {
  const calendarElement = document.getElementById('calendar');
  if (!calendarElement) return;
  
  // Si FullCalendar n'est pas défini, le charger dynamiquement
  if (typeof FullCalendar === 'undefined') {
    console.log('FullCalendar n\'est pas défini, chargement dynamique...');
    return;
  }
  
  // Ajouter des animations aux événements
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.addedNodes.length) {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1 && node.classList && node.classList.contains('fc-event')) {
            enhanceCalendarEvent(node);
          }
        });
      }
    });
  });
  
  observer.observe(calendarElement, { childList: true, subtree: true });
  
  // Ajouter des animations aux événements existants
  const events = calendarElement.querySelectorAll('.fc-event');
  events.forEach(event => enhanceCalendarEvent(event));
}

/**
 * Améliore les événements du calendrier
 */
function enhanceCalendarEvent(eventElement) {
  eventElement.classList.add('calendar-event-enhanced');
  
  // Ajouter une animation au survol
  eventElement.addEventListener('mouseenter', () => {
    eventElement.style.transform = 'translateY(-2px)';
    eventElement.style.boxShadow = 'var(--shadow-md)';
    eventElement.style.zIndex = '5';
  });
  
  eventElement.addEventListener('mouseleave', () => {
    eventElement.style.transform = '';
    eventElement.style.boxShadow = '';
    eventElement.style.zIndex = '';
  });
}

/**
 * Initialise les tooltips
 */
function initTooltips() {
  // Utiliser Tippy.js si disponible
  if (typeof tippy === 'function') {
    tippy('[title]:not(.fc-event)', {
      placement: 'top',
      arrow: true,
      theme: 'light-border',
      duration: 200,
      delay: [300, 0]
    });
  } else {
    // Fallback pour les navigateurs qui ne supportent pas Tippy.js
    document.querySelectorAll('[title]').forEach(el => {
      const title = el.getAttribute('title');
      if (title) {
        el.addEventListener('mouseenter', () => {
          const tooltip = document.createElement('div');
          tooltip.className = 'simple-tooltip';
          tooltip.textContent = title;
          tooltip.style.position = 'absolute';
          tooltip.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
          tooltip.style.color = 'white';
          tooltip.style.padding = '5px 8px';
          tooltip.style.borderRadius = '4px';
          tooltip.style.fontSize = '12px';
          tooltip.style.zIndex = '9999';
          
          document.body.appendChild(tooltip);
          
          const rect = el.getBoundingClientRect();
          tooltip.style.top = (rect.top - tooltip.offsetHeight - 5) + 'px';
          tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
          
          el.addEventListener('mouseleave', () => {
            document.body.removeChild(tooltip);
          }, { once: true });
        });
      }
    });
  }
}

/**
 * Remplace les badges statiques par des badges dynamiques
 */
function enhanceBadges() {
  // Remplacer les badges de statut
  document.querySelectorAll('.badge').forEach(badge => {
    const text = badge.textContent.trim().toLowerCase();
    
    if (badge.classList.contains('bg-success') || text.includes('confirmé') || text.includes('confirmed')) {
      replaceBadge(badge, 'confirmed', 'Confirmé', 'check-circle');
    } else if (badge.classList.contains('bg-warning') || text.includes('attente') || text.includes('waiting')) {
      replaceBadge(badge, 'waiting', 'En attente', 'clock');
    } else if (badge.classList.contains('bg-danger') || text.includes('annulé') || text.includes('canceled')) {
      replaceBadge(badge, 'canceled', 'Annulé', 'times-circle');
    }
  });
}

/**
 * Remplace un badge par un badge amélioré
 */
function replaceBadge(badge, type, text, icon) {
  const newBadge = document.createElement('span');
  newBadge.className = `badge-status ${type}`;
  newBadge.innerHTML = `<i class="fas fa-${icon}"></i> ${text}`;
  
  badge.parentNode.replaceChild(newBadge, badge);
}

/**
 * Affiche un message de secours si une bibliothèque ne peut pas être chargée
 */
function showFallbackNotification(libraryName) {
  const container = document.createElement('div');
  container.className = 'fallback-notification';
  container.innerHTML = `
    <div class="fallback-content">
      <i class="fas fa-exclamation-triangle"></i>
      <div>
        <h3>Fonctionnalité limitée</h3>
        <p>La bibliothèque ${libraryName} n'a pas pu être chargée. Certaines fonctionnalités peuvent être indisponibles.</p>
      </div>
      <button class="close-btn"><i class="fas fa-times"></i></button>
    </div>
  `;
  
  document.body.appendChild(container);
  
  // Fermer la notification
  const closeBtn = container.querySelector('.close-btn');
  closeBtn.addEventListener('click', () => {
    container.classList.add('fade-out');
    setTimeout(() => {
      if (container.parentNode === document.body) {
        document.body.removeChild(container);
      }
    }, 500);
  });
  
  // Auto-fermeture après 8 secondes
  setTimeout(() => {
    container.classList.add('fade-out');
    setTimeout(() => {
      if (container.parentNode === document.body) {
        document.body.removeChild(container);
      }
    }, 500);
  }, 8000);
}

/**
 * Affiche un indicateur de chargement lors de la soumission d'un formulaire
 */
function showLoadingIndicator(form) {
  const submitBtn = form.querySelector('button[type="submit"]');
  
  if (submitBtn) {
    // Stocker le contenu original du bouton
    const originalContent = submitBtn.innerHTML;
    
    // Remplacer par un spinner
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Traitement en cours...';
    
    // Restaurer après un certain délai si la page ne s'est pas rechargée
    setTimeout(() => {
      if (document.body.contains(submitBtn)) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalContent;
      }
    }, 10000); // 10 secondes maximum
  }
}

/**
 * Affiche une erreur de formulaire
 */
function showFormError(message) {
  // Créer ou mettre à jour le message d'erreur du formulaire
  let errorContainer = document.querySelector('.form-error-message');
  
  if (!errorContainer) {
    errorContainer = document.createElement('div');
    errorContainer.className = 'form-error-message alert alert-danger animate__animated animate__shakeX';
    
    // Trouver où ajouter le message d'erreur
    const form = document.querySelector('form');
    if (form) {
      form.prepend(errorContainer);
    } else {
      document.body.prepend(errorContainer);
    }
  }
  
  errorContainer.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
  errorContainer.style.display = 'block';
  
  // Faire défiler jusqu'au message d'erreur
  errorContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
  
  // Ajouter l'animation pour attirer l'attention
  errorContainer.classList.remove('animate__shakeX');
  void errorContainer.offsetWidth; // Force reflow
  errorContainer.classList.add('animate__shakeX');
}

/**
 * Fonctions de validation
 */
function isValidEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

function isValidPhone(phone) {
  // Format international ou français
  const re = /^(\+\d{1,3})?[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}$/;
  return re.test(phone);
}

function isValidDate(date) {
  const d = parseDate(date);
  return !isNaN(d.getTime());
}

/**
 * Parse une date dans différents formats
 */
function parseDate(dateStr) {
  // Essayer différents formats de date
  if (!dateStr) return new Date(NaN);
  
  // Format ISO
  if (/^\d{4}-\d{2}-\d{2}/.test(dateStr)) {
    return new Date(dateStr);
  }
  
  // Format français (DD/MM/YYYY)
  if (/^\d{2}\/\d{2}\/\d{4}/.test(dateStr)) {
    const parts = dateStr.split('/');
    return new Date(parts[2], parts[1] - 1, parts[0]);
  }
  
  // Format avec texte (e.g., "15 Mai 2025")
  const months = {
    'janvier': 0, 'fevrier': 1, 'février': 1, 'mars': 2, 'avril': 3, 'mai': 4, 'juin': 5,
    'juillet': 6, 'aout': 7, 'août': 7, 'septembre': 8, 'octobre': 9, 'novembre': 10, 'decembre': 11, 'décembre': 11
  };
  
  const match = dateStr.match(/(\d+)\s+(\w+)\s+(\d{4})/i);
  if (match) {
    const day = parseInt(match[1]);
    const monthStr = match[2].toLowerCase();
    const year = parseInt(match[3]);
    
    if (months[monthStr] !== undefined) {
      return new Date(year, months[monthStr], day);
    }
  }
  
  // Dernier essai avec le constructeur Date
  return new Date(dateStr);
}

// Exposer certaines fonctions à l'usage global
window.enhancedUI = {
  showToast,
  validateInput,
  isValidEmail,
  isValidPhone,
  isValidDate,
  showFormError,
  showLoadingIndicator
};