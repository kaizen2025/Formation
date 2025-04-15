/**
 * Système de Réservation des Formations Anecoop
 * main.js - Fonctionnalités JavaScript communes (version améliorée)
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les événements
    initNotifications();
    initModals();
    initThemeToggle();
    initHelpTabs();
    initFormValidation();
    updateSyncStatus('connecting');
    
    // Tester la connexion à la base de données
    checkDatabaseConnection()
        .then(connected => {
            if (connected) {
                updateSyncStatus('connected');
            } else {
                updateSyncStatus('offline');
            }
        })
        .catch(() => {
            updateSyncStatus('error');
        });
        
    // Initialiser les tooltips si Tippy.js est disponible
    if (typeof tippy === 'function') {
        initTooltips();
    } else {
        // Charger dynamiquement Tippy.js s'il n'est pas disponible
        loadScript('https://cdn.jsdelivr.net/npm/tippy.js@6.3.7/dist/tippy-bundle.umd.min.js')
            .then(() => {
                console.log('Tippy.js chargé dynamiquement');
                initTooltips();
            })
            .catch(() => {
                console.warn('Impossible de charger Tippy.js');
            });
    }
    
    // Initialiser les composants interactifs
    initInteractiveComponents();
    
    // Initialiser le dropdown utilisateur
    initUserDropdown();
});

/**
 * Charge un script dynamiquement
 * @param {string} src - URL du script
 * @returns {Promise} Promise résolue quand le script est chargé
 */
function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

/**
 * Vérifie si la connexion à la base de données est possible
 * @returns {Promise<boolean>} True si la connexion est possible
 */
async function checkDatabaseConnection() {
    try {
        const response = await fetch('/api/ping');
        return response.ok;
    } catch (error) {
        console.error('Erreur lors de la vérification de connexion:', error);
        return false;
    }
}

/**
 * Initialise le système de notifications
 */
function initNotifications() {
    const notificationsBtn = document.getElementById('notificationsBtn');
    const notificationsPanel = document.getElementById('notifications-panel');
    const clearNotifications = document.getElementById('clearNotifications');
    
    if (notificationsBtn && notificationsPanel) {
        // Ouvrir/fermer le panneau de notifications
        notificationsBtn.addEventListener('click', function() {
            if (notificationsPanel.classList.contains('hidden')) {
                notificationsPanel.classList.remove('hidden');
                loadNotifications();
            } else {
                notificationsPanel.classList.add('hidden');
            }
        });
        
        // Fermer les notifications en cliquant en dehors
        document.addEventListener('click', function(event) {
            if (notificationsPanel && 
                !notificationsPanel.classList.contains('hidden') && 
                !notificationsPanel.contains(event.target) && 
                event.target !== notificationsBtn) {
                notificationsPanel.classList.add('hidden');
            }
        });
        
        // Effacer toutes les notifications
        if (clearNotifications) {
            clearNotifications.addEventListener('click', function() {
                clearAllNotifications();
                notificationsPanel.classList.add('hidden');
            });
        }
    }
    
    // Charger les notifications au démarrage
    loadNotifications();
}

/**
 * Charge les notifications depuis le stockage local
 */
function loadNotifications() {
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
        const formattedDate = `${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
        
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
            markNotification(index, !notifications[index].read);
        });
    });
}

/**
 * Marque une notification comme lue/non lue
 * @param {number} index - Index de la notification
 * @param {boolean} read - True pour marquer comme lue, false pour non lue
 */
function markNotification(index, read) {
    const notifications = JSON.parse(localStorage.getItem('anecoop-notifications')) || [];
    
    if (index >= 0 && index < notifications.length) {
        notifications[index].read = read;
        localStorage.setItem('anecoop-notifications', JSON.stringify(notifications));
        loadNotifications();
    }
}

/**
 * Efface toutes les notifications
 */
function clearAllNotifications() {
    localStorage.setItem('anecoop-notifications', JSON.stringify([]));
    loadNotifications();
    
    showToast('Notifications effacées', 'Toutes les notifications ont été effacées.', 'info');
}

/**
 * Ajoute une notification
 * @param {string} title - Titre de la notification
 * @param {string} message - Message de la notification
 * @param {string} type - Type de notification (success, error, warning, info)
 */
function addNotification(title, message, type = 'info') {
    // Créer la notification
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
    loadNotifications();
    
    // Afficher un toast
    showToast(title, message, type);
}

/**
 * Initialise les gestionnaires d'événements pour les modales
 */
function initModals() {
    // Gestionnaire pour le bouton de feedback
    const feedbackBtn = document.getElementById('feedbackBtn');
    const feedbackModal = document.getElementById('feedbackModal');
    const closeFeedback = document.getElementById('closeFeedback');
    const submitFeedback = document.getElementById('submitFeedback');
    
    // S'assurer que toutes les modales sont cachées au démarrage
    document.querySelectorAll('.modal').forEach(modal => {
        if (!modal.classList.contains('hidden')) {
            modal.classList.add('hidden');
        }
    });
    
    if (feedbackBtn && feedbackModal) {
        feedbackBtn.addEventListener('click', function() {
            feedbackModal.classList.remove('hidden');
        });
        
        // Fermer la modale avec le bouton de fermeture
        if (closeFeedback) {
            closeFeedback.addEventListener('click', function() {
                feedbackModal.classList.add('hidden');
            });
        }
        
        // Fermer la modale en cliquant en dehors
        feedbackModal.addEventListener('click', function(e) {
            if (e.target === feedbackModal) {
                feedbackModal.classList.add('hidden');
            }
        });
    }
    
    if (submitFeedback) {
        submitFeedback.addEventListener('click', function() {
            const form = document.getElementById('feedbackForm');
            const formData = new FormData(form);
            
            // Créer les données de feedback
            const feedbackData = {
                type: formData.get('type'),
                message: formData.get('message'),
                email: formData.get('email')
            };
            
            // Valider
            if (!feedbackData.message) {
                showToast('Erreur', 'Veuillez saisir votre message de feedback.', 'error');
                return;
            }
            
            // Désactiver le bouton
            submitFeedback.disabled = true;
            submitFeedback.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Envoi...';
            
            // Envoyer le feedback
            fetch('/api/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(feedbackData)
            })
            .then(response => {
                // Vérifier la réponse HTTP
                if (!response.ok) {
                    throw new Error(`Erreur HTTP: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Réactiver le bouton
                submitFeedback.disabled = false;
                submitFeedback.innerHTML = '<i class="fas fa-paper-plane"></i> Envoyer';
                
                if (data.id) {
                    // Réinitialiser le formulaire
                    form.reset();
                    
                    // Fermer la modal
                    feedbackModal.classList.add('hidden');
                    
                    // Afficher un message de succès
                    showToast('Merci pour votre feedback !', 'Votre message a été envoyé avec succès.', 'success');
                } else {
                    throw new Error(data.error || 'Une erreur est survenue lors de l\'envoi');
                }
            })
            .catch(error => {
                console.error('Erreur lors de l\'envoi du feedback:', error);
                
                // Réactiver le bouton
                submitFeedback.disabled = false;
                submitFeedback.innerHTML = '<i class="fas fa-paper-plane"></i> Envoyer';
                
                showToast('Erreur', 'Une erreur est survenue lors de l\'envoi de votre feedback.', 'error');
            });
        });
    }
    
    // Gestionnaire pour le bouton d'aide
    const helpBtn = document.getElementById('helpBtn');
    const helpModal = document.getElementById('helpModal');
    const closeHelp = document.getElementById('closeHelp');
    
    if (helpBtn && helpModal) {
        helpBtn.addEventListener('click', function() {
            helpModal.classList.remove('hidden');
        });
        
        // Fermer la modale avec le bouton de fermeture
        if (closeHelp) {
            closeHelp.addEventListener('click', function() {
                helpModal.classList.add('hidden');
            });
        }
        
        // Fermer la modale en cliquant en dehors
        helpModal.addEventListener('click', function(e) {
            if (e.target === helpModal) {
                helpModal.classList.add('hidden');
            }
        });
    }
    
    // Fermer les modales avec la touche Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal:not(.hidden)').forEach(modal => {
                modal.classList.add('hidden');
            });
        }
    });
}

/**
 * Initialise des composants interactifs pour améliorer l'expérience utilisateur
 */
function initInteractiveComponents() {
    // Animation des cartes et éléments interactifs
    document.querySelectorAll('.card, .dashboard-card, .form-group, .info-card').forEach(el => {
        el.classList.add('animate__animated', 'animate__fadeIn');
    });
    
    // Améliorer les boutons avec des effets visuels
    document.querySelectorAll('.btn, .icon-btn, .primary-btn, .secondary-btn').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
    
    // Initialiser les éléments de sélection améliorés
    initEnhancedSelects();
    
    // Initialiser la recherche
    initSearch();
}

/**
 * Initialise les éléments de sélection améliorés
 */
function initEnhancedSelects() {
    const selects = document.querySelectorAll('select:not(.form-control)');
    
    selects.forEach(select => {
        // Ignorer les selects déjà initialisés
        if (select.parentNode.classList.contains('enhanced-select-container')) {
            return;
        }
        
        // Créer le conteneur
        const container = document.createElement('div');
        container.className = 'enhanced-select-container';
        
        // Wrapper l'élément select
        select.parentNode.insertBefore(container, select);
        container.appendChild(select);
        
        // Ajouter l'icône
        const icon = document.createElement('i');
        icon.className = 'fas fa-chevron-down select-arrow';
        container.appendChild(icon);
        
        // Attacher un événement pour l'animation
        select.addEventListener('focus', () => {
            container.classList.add('focused');
        });
        
        select.addEventListener('blur', () => {
            container.classList.remove('focused');
        });
    });
}

/**
 * Initialise la recherche
 */
function initSearch() {
    const searchBtn = document.getElementById('searchBtn');
    const searchOverlay = document.getElementById('search-overlay');
    const closeSearch = document.getElementById('closeSearch');
    const searchInput = document.getElementById('searchInput');
    
    if (searchBtn && searchOverlay && closeSearch) {
        searchBtn.addEventListener('click', function() {
            searchOverlay.classList.remove('hidden');
            if (searchInput) searchInput.focus();
        });
        
        closeSearch.addEventListener('click', function() {
            searchOverlay.classList.add('hidden');
        });
        
        // Fermer la recherche avec Escape
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && !searchOverlay.classList.contains('hidden')) {
                searchOverlay.classList.add('hidden');
            }
        });
        
        // Empêcher la propagation des clics dans le contenu de la recherche
        searchOverlay.querySelector('.search-container').addEventListener('click', function(e) {
            e.stopPropagation();
        });
        
        // Fermer la recherche en cliquant en dehors
        searchOverlay.addEventListener('click', function() {
            searchOverlay.classList.add('hidden');
        });
        
        // Recherche en temps réel avec debounce
        if (searchInput) {
            let debounceTimer;
            
            searchInput.addEventListener('input', function() {
                clearTimeout(debounceTimer);
                
                if (this.value.length >= 2) {
                    debounceTimer = setTimeout(() => {
                        performSearch(this.value);
                    }, 300);
                } else if (this.value.length === 0) {
                    document.getElementById('searchResults').innerHTML = '';
                }
            });
            
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    clearTimeout(debounceTimer);
                    performSearch(this.value);
                }
            });
            
            const submitSearch = document.getElementById('submitSearch');
            if (submitSearch) {
                submitSearch.addEventListener('click', function() {
                    performSearch(searchInput.value);
                });
            }
        }
    }
}

/**
 * Exécute une recherche
 * @param {string} query - Requête de recherche
 */
function performSearch(query) {
    if (!query || query.length < 2) {
        document.getElementById('searchResults').innerHTML = '';
        return;
    }
    
    const searchResults = document.getElementById('searchResults');
    
    // Afficher un indicateur de chargement
    searchResults.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Recherche en cours...</span>
            </div>
            <p>Recherche en cours...</p>
        </div>
    `;
    
    // Simuler un délai (en production, on ferait un appel à l'API)
    // NOTE: Dans une version réelle, remplacer par un appel à l'API
    setTimeout(() => {
        // Liste de résultats de recherche simulés
        // Dans une version réelle, ces données viendraient de l'API
        const dummyResults = [
            { 
                type: 'formation', 
                title: 'Communiquer avec Teams', 
                date: '15/05/2025', 
                description: 'Formation sur l\'utilisation de Microsoft Teams pour la communication d\'équipe',
                url: '/formations?formation=teams-communication'
            },
            { 
                type: 'formation', 
                title: 'Collaborer avec Teams/SharePoint', 
                date: '22/05/2025', 
                description: 'Formation sur l\'utilisation de Teams et SharePoint pour la collaboration documentaire',
                url: '/formations?formation=teams-sharepoint'
            },
            { 
                type: 'participant', 
                title: 'Jean Dupont', 
                date: '', 
                description: 'Département: Commerce | Email: jean.dupont@anecoop.fr',
                url: '/participants?id=123'
            }
        ];
        
        // Filtrer les résultats selon la requête
        const results = dummyResults.filter(result => 
            result.title.toLowerCase().includes(query.toLowerCase()) ||
            result.description.toLowerCase().includes(query.toLowerCase())
        );
        
        if (results.length === 0) {
            searchResults.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-search fa-3x mb-3"></i>
                    <p>Aucun résultat trouvé pour "${query}"</p>
                    <p class="small">Essayez avec des termes différents ou vérifiez l'orthographe</p>
                </div>
            `;
            return;
        }
        
        let html = `<h4>Résultats de recherche (${results.length})</h4>`;
        html += '<div class="list-group">';
        
        results.forEach(result => {
            let icon = 'calendar-alt';
            
            switch (result.type) {
                case 'formation':
                    icon = 'chalkboard-teacher';
                    break;
                case 'participant':
                    icon = 'user';
                    break;
                case 'document':
                    icon = 'file-alt';
                    break;
            }
            
            html += `
                <a href="${result.url}" class="list-group-item list-group-item-action">
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1"><i class="fas fa-${icon}"></i> ${result.title}</h5>
                        <small class="text-muted">${result.date || ''}</small>
                    </div>
                    <p class="mb-1">${result.description || ''}</p>
                    <small class="text-muted">${result.type.charAt(0).toUpperCase() + result.type.slice(1)}</small>
                </a>
            `;
        });
        
        html += '</div>';
        searchResults.innerHTML = html;
    }, 500);
}

/**
 * Initialise le toggle de thème
 */
function initThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    
    if (themeToggle) {
        // Vérifier le thème sauvegardé
        const savedTheme = localStorage.getItem('anecoop-theme');
        
        // Vérifier également la préférence du système
        const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        // Appliquer le thème sauvegardé ou la préférence du système
        if (savedTheme === 'dark' || (savedTheme === null && prefersDarkMode)) {
            document.body.classList.add('dark-mode');
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            themeToggle.setAttribute('title', 'Passer en mode clair');
        } else {
            themeToggle.setAttribute('title', 'Passer en mode sombre');
        }
        
        // Gérer le changement de thème
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            
            if (document.body.classList.contains('dark-mode')) {
                themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                themeToggle.setAttribute('title', 'Passer en mode clair');
                localStorage.setItem('anecoop-theme', 'dark');
            } else {
                themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
                themeToggle.setAttribute('title', 'Passer en mode sombre');
                localStorage.setItem('anecoop-theme', 'light');
            }
            
            // Animer le changement de thème
            document.body.classList.add('theme-transition');
            setTimeout(() => {
                document.body.classList.remove('theme-transition');
            }, 500);
        });
        
        // Suivre les changements de préférence système
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
                // Uniquement si l'utilisateur n'a pas explicitement choisi un thème
                if (!localStorage.getItem('anecoop-theme')) {
                    if (e.matches) {
                        document.body.classList.add('dark-mode');
                        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                    } else {
                        document.body.classList.remove('dark-mode');
                        themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
                    }
                }
            });
        }
    }
}

/**
 * Initialise le dropdown utilisateur
 */
function initUserDropdown() {
    const userDropdown = document.querySelector('.user-dropdown');
    if (userDropdown) {
        const dropdownToggle = userDropdown.querySelector('.dropdown-toggle');
        const dropdownMenu = userDropdown.querySelector('.dropdown-menu');
        
        if (dropdownToggle && dropdownMenu) {
            // Si Bootstrap est disponible, utiliser ses fonctions
            if (typeof bootstrap !== 'undefined' && bootstrap.Dropdown) {
                return; // Bootstrap s'occupera du dropdown
            }
            
            // Sinon, implémenter un fallback
            dropdownToggle.addEventListener('click', function(e) {
                e.preventDefault();
                dropdownMenu.classList.toggle('show');
            });
            
            // Fermer le dropdown en cliquant en dehors
            document.addEventListener('click', function(e) {
                if (!userDropdown.contains(e.target)) {
                    dropdownMenu.classList.remove('show');
                }
            });
        }
    }
}

/**
 * Initialise les onglets d'aide
 */
function initHelpTabs() {
    const helpTabs = document.querySelectorAll('.help-tab');
    const helpContents = document.querySelectorAll('.help-tab-content');
    
    helpTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Supprimer la classe active de tous les onglets et contenus
            helpTabs.forEach(t => t.classList.remove('active'));
            helpContents.forEach(c => c.classList.remove('active'));
            
            // Ajouter la classe active à l'onglet cliqué
            this.classList.add('active');
            
            // Afficher le contenu correspondant
            const tabId = this.getAttribute('data-tab');
            const content = document.getElementById(`${tabId}Help`);
            if (content) {
                content.classList.add('active');
                
                // Animation d'apparition
                content.style.opacity = '0';
                content.style.transform = 'translateY(10px)';
                
                setTimeout(() => {
                    content.style.transition = 'opacity 0.3s, transform 0.3s';
                    content.style.opacity = '1';
                    content.style.transform = 'translateY(0)';
                }, 50);
            }
        });
    });
}

/**
 * Initialise la validation des formulaires
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // Ne pas ajouter de validation aux formulaires de recherche ou aux formulaires avec data-novalidate
        if (form.classList.contains('search-form') || form.hasAttribute('data-novalidate')) {
            return;
        }
        
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
        
        // Validation à la soumission
        form.addEventListener('submit', function(e) {
            let isValid = true;
            
            // Vérifier les champs requis
            form.querySelectorAll('[required]').forEach(field => {
                if (!validateInput(field, true)) {
                    isValid = false;
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                e.stopPropagation();
                
                // Afficher un message d'erreur
                showToast('Erreur de validation', 'Veuillez corriger les erreurs dans le formulaire.', 'error');
                
                // Faire défiler jusqu'au premier champ en erreur
                const firstError = form.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstError.focus();
                }
            } else {
                // Désactiver le bouton de soumission pour éviter les doubles soumissions
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    
                    // Stocker le texte original
                    const originalHtml = submitBtn.innerHTML;
                    
                    // Remplacer par un spinner
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Traitement en cours...';
                    
                    // Réactiver le bouton après 10s (au cas où la soumission échoue)
                    setTimeout(() => {
                        if (document.body.contains(submitBtn)) {
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = originalHtml;
                        }
                    }, 10000);
                }
            }
        });
    });
}

/**
 * Valide un champ de formulaire
 * @param {HTMLElement} input - Élément de formulaire à valider
 * @param {boolean} showError - Afficher les erreurs
 * @returns {boolean} - True si le champ est valide
 */
function validateInput(input, showError = false) {
    let isValid = true;
    let errorMessage = '';
    
    // Vérifier si le champ est requis
    if (input.hasAttribute('required') && !input.value.trim()) {
        isValid = false;
        errorMessage = 'Ce champ est requis';
    }
    
    // Valider en fonction du type
    if (input.value.trim()) {
        if (input.type === 'email' && !isValidEmail(input.value)) {
            isValid = false;
            errorMessage = 'Adresse email invalide';
        } else if (input.type === 'tel' && !isValidPhone(input.value)) {
            isValid = false;
            errorMessage = 'Numéro de téléphone invalide';
        } else if (input.type === 'date' && !isValidDate(input.value)) {
            isValid = false;
            errorMessage = 'Date invalide';
        } else if (input.type === 'url' && !isValidUrl(input.value)) {
            isValid = false;
            errorMessage = 'URL invalide';
        }
    }
    
    // Validation des attributs pattern
    if (input.hasAttribute('pattern') && input.value.trim()) {
        const pattern = new RegExp(input.getAttribute('pattern'));
        if (!pattern.test(input.value)) {
            isValid = false;
            errorMessage = input.getAttribute('data-error-message') || 'Format invalide';
        }
    }
    
    // Validation de longueur
    if (input.hasAttribute('minlength') && input.value.trim()) {
        const minLength = parseInt(input.getAttribute('minlength'));
        if (input.value.length < minLength) {
            isValid = false;
            errorMessage = `Minimum ${minLength} caractères requis`;
        }
    }
    
    // Afficher l'erreur si demandé
    if (showError) {
        // Trouver ou créer le conteneur d'erreur
        let errorContainer = input.nextElementSibling;
        if (!errorContainer || !errorContainer.classList.contains('invalid-feedback')) {
            errorContainer = document.createElement('div');
            errorContainer.className = 'invalid-feedback';
            input.parentNode.insertBefore(errorContainer, input.nextSibling);
        }
        
        // Mettre à jour le message d'erreur
        errorContainer.textContent = errorMessage;
        
        // Mettre à jour les classes sur le champ
        input.classList.toggle('is-invalid', !isValid);
        if (isValid && input.value.trim()) {
            input.classList.add('is-valid');
        } else {
            input.classList.remove('is-valid');
        }
    }
    
    return isValid;
}

/**
 * Initialise les tooltips
 */
function initTooltips() {
    if (typeof tippy === 'function') {
        // Initialiser les tooltips pour tous les éléments avec un attribut title
        tippy('[title]', {
            placement: 'top',
            arrow: true,
            theme: 'light-border',
            duration: 200
        });
    }
}

/**
 * Met à jour l'indicateur de synchronisation
 * @param {string} status - Statut de synchronisation 
 * ('connecting', 'connected', 'syncing', 'offline', 'error')
 */
function updateSyncStatus(status) {
    const syncStatus = document.getElementById('syncStatus');
    if (!syncStatus) {
        return;
    }
    
    switch (status) {
        case 'connecting':
            syncStatus.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Connexion à la base de données...';
            syncStatus.className = 'sync-indicator';
            break;
            
        case 'connected':
            syncStatus.innerHTML = '<i class="fas fa-check-circle"></i> Connecté à la base de données';
            syncStatus.className = 'sync-indicator connected';
            break;
            
        case 'syncing':
            syncStatus.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Synchronisation en cours...';
            syncStatus.className = 'sync-indicator syncing';
            break;
            
        case 'offline':
            syncStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Mode hors ligne (données locales)';
            syncStatus.className = 'sync-indicator offline';
            break;
            
        case 'error':
            syncStatus.innerHTML = '<i class="fas fa-exclamation-circle"></i> Erreur de synchronisation';
            syncStatus.className = 'sync-indicator error';
            break;
            
        default:
            syncStatus.innerHTML = '<i class="fas fa-question-circle"></i> Statut inconnu';
            syncStatus.className = 'sync-indicator';
    }
}

/**
 * Affiche une notification toast
 * @param {string} title - Titre de la notification
 * @param {string} message - Message de la notification
 * @param {string} type - Type de notification (success, error, warning, info)
 */
function showToast(title, message, type = 'info') {
    // Déterminer la couleur selon le type
    let bgColor;
    
    switch (type) {
        case 'success':
            bgColor = '#48bb78';
            break;
        case 'warning':
            bgColor = '#f6ad55';
            break;
        case 'error':
            bgColor = '#e53e3e';
            break;
        default: // info
            bgColor = '#3498db';
            break;
    }
    
    // Vérifier si Toastify est disponible
    if (typeof Toastify === 'function') {
        Toastify({
            text: `<b>${title}</b><br>${message}`,
            duration: 4000,
            gravity: "bottom",
            position: "right",
            backgroundColor: bgColor,
            stopOnFocus: true,
            className: 'toast-notification',
            escapeMarkup: false,
            onClick: function() {
                // Ouvrir les notifications
                document.getElementById('notificationsBtn')?.click();
            }
        }).showToast();
    } else {
        // Fallback si Toastify n'est pas disponible
        const toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        toastContainer.style.position = 'fixed';
        toastContainer.style.bottom = '20px';
        toastContainer.style.right = '20px';
        toastContainer.style.zIndex = '9999';
        
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.style.backgroundColor = 'white';
        toast.style.color = '#333';
        toast.style.padding = '12px 15px';
        toast.style.borderRadius = '4px';
        toast.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
        toast.style.marginBottom = '10px';
        toast.style.minWidth = '250px';
        toast.style.borderLeft = `4px solid ${bgColor}`;
        
        toast.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 5px;">${title}</div>
            <div>${message}</div>
        `;
        
        toastContainer.appendChild(toast);
        document.body.appendChild(toastContainer);
        
        // Supprimer après 4 secondes
        setTimeout(() => {
            document.body.removeChild(toastContainer);
        }, 4000);
    }
    
    // Ajouter à la liste des notifications
    addNotification(title, message, type);
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
    const d = new Date(date);
    return !isNaN(d.getTime());
}

function isValidUrl(url) {
    try {
        new URL(url);
        return true;
    } catch (e) {
        return false;
    }
}

/**
 * Fonctions pour l'export de données
 */

/**
 * Exporte des données au format CSV
 * @param {Array} data - Tableau d'objets à exporter
 * @param {string} filename - Nom du fichier
 */
function exportToCSV(data, filename = 'export.csv') {
    if (!data || !data.length) {
        showToast('Erreur', 'Aucune donnée à exporter', 'error');
        return;
    }
    
    // Récupérer les en-têtes à partir des clés du premier objet
    const headers = Object.keys(data[0]);
    
    // Créer les lignes CSV
    const csvRows = [];
    
    // Ajouter l'en-tête
    csvRows.push(headers.join(','));
    
    // Ajouter les données
    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            const escaped = typeof value === 'string' ? `"${value.replace(/"/g, '""')}"` : value;
            return escaped;
        });
        csvRows.push(values.join(','));
    }
    
    // Combiner en une seule chaîne
    const csvString = csvRows.join('\n');
    
    // Créer un Blob et le télécharger
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    showToast('Succès', `Exportation terminée : ${filename}`, 'success');
}

/**
 * Exporte des données au format Excel
 * @param {Array} data - Tableau d'objets à exporter
 * @param {string} sheetName - Nom de la feuille
 * @param {string} filename - Nom du fichier
 */
function exportToExcel(data, sheetName = 'Sheet1', filename = 'export.xlsx') {
    if (!data || !data.length) {
        showToast('Erreur', 'Aucune donnée à exporter', 'error');
        return;
    }
    
    // Vérifier si SheetJS est disponible
    if (typeof XLSX === 'undefined') {
        // Tenter de charger SheetJS dynamiquement
        showToast('Chargement', 'Chargement de la bibliothèque d\'export Excel...', 'info');
        
        loadScript('https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js')
            .then(() => {
                // Tenter l'export à nouveau après le chargement
                setTimeout(() => exportToExcel(data, sheetName, filename), 500);
            })
            .catch(() => {
                showToast('Erreur', 'Impossible de charger la bibliothèque d\'export Excel', 'error');
            });
        return;
    }
    
    try {
        // Créer un nouveau classeur
        const wb = XLSX.utils.book_new();
        
        // Créer une feuille de calcul
        const ws = XLSX.utils.json_to_sheet(data);
        
        // Ajouter la feuille au classeur
        XLSX.utils.book_append_sheet(wb, ws, sheetName);
        
        // Générer le fichier Excel
        XLSX.writeFile(wb, filename);
        
        showToast('Succès', `Exportation terminée : ${filename}`, 'success');
    } catch (error) {
        console.error('Erreur lors de l\'exportation Excel:', error);
        showToast('Erreur', 'Une erreur est survenue lors de l\'exportation Excel', 'error');
    }
}

/**
 * Exporte une section de page au format PDF
 * @param {string} elementId - ID de l'élément à exporter
 * @param {string} filename - Nom du fichier
 */
function exportToPDF(elementId, filename = 'export.pdf') {
    const element = document.getElementById(elementId);
    
    if (!element) {
        showToast('Erreur', 'Élément non trouvé', 'error');
        return;
    }
    
    // Vérifier si jsPDF et html2canvas sont disponibles
    const jspdfMissing = typeof jspdf === 'undefined';
    const html2canvasMissing = typeof html2canvas === 'undefined';
    
    if (jspdfMissing || html2canvasMissing) {
        showToast('Chargement', 'Chargement des bibliothèques d\'export PDF...', 'info');
        
        // Charger les bibliothèques manquantes
        const promises = [];
        
        if (jspdfMissing) {
            promises.push(loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'));
        }
        
        if (html2canvasMissing) {
            promises.push(loadScript('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js'));
        }
        
        Promise.all(promises)
            .then(() => {
                // Tenter l'export à nouveau après le chargement
                setTimeout(() => exportToPDF(elementId, filename), 500);
            })
            .catch(() => {
                showToast('Erreur', 'Impossible de charger les bibliothèques d\'export PDF', 'error');
            });
        return;
    }
    
    try {
        showToast('Information', 'Génération du PDF en cours...', 'info');
        
        // Créer une copie de l'élément pour ne pas affecter l'original
        const clonedElement = element.cloneNode(true);
        clonedElement.style.background = 'white';
        clonedElement.style.padding = '20px';
        
        // Cacher les boutons et éléments inutiles pour l'export
        clonedElement.querySelectorAll('.no-print, button, .actions-container').forEach(el => {
            el.style.display = 'none';
        });
        
        // Ajouter temporairement à la page
        clonedElement.style.position = 'absolute';
        clonedElement.style.left = '-9999px';
        document.body.appendChild(clonedElement);
        
        // Convertir en canvas
        html2canvas(clonedElement, {
            scale: 2,
            useCORS: true,
            logging: false
        }).then(canvas => {
            // Supprimer l'élément temporaire
            document.body.removeChild(clonedElement);
            
            // Créer le PDF
            const pdf = new jspdf.jsPDF({
                orientation: 'portrait',
                unit: 'mm',
                format: 'a4'
            });
            
            const imgData = canvas.toDataURL('image/png');
            const pdfWidth = pdf.internal.pageSize.getWidth();
            const pdfHeight = pdf.internal.pageSize.getHeight();
            const imgWidth = canvas.width;
            const imgHeight = canvas.height;
            const ratio = Math.min(pdfWidth / imgWidth, pdfHeight / imgHeight);
            const imgX = (pdfWidth - imgWidth * ratio) / 2;
            const imgY = 30;
            
            // Ajouter l'en-tête
            pdf.setFontSize(18);
            pdf.setTextColor(44, 110, 203); // Primary color
            pdf.text('Anecoop Formations', pdfWidth / 2, 15, { align: 'center' });
            
            // Ajouter l'image
            pdf.addImage(imgData, 'PNG', imgX, imgY, imgWidth * ratio, imgHeight * ratio);
            
            // Ajouter un pied de page
            pdf.setFontSize(10);
            pdf.setTextColor(100, 100, 100);
            const today = new Date();
            pdf.text(`Document généré le ${today.toLocaleDateString()} à ${today.toLocaleTimeString()}`, pdfWidth / 2, pdfHeight - 10, { align: 'center' });
            
            // Télécharger le PDF
            pdf.save(filename);
            
            showToast('Succès', `PDF généré avec succès : ${filename}`, 'success');
        });
    } catch (error) {
        console.error('Erreur lors de l\'exportation PDF:', error);
        showToast('Erreur', 'Une erreur est survenue lors de la génération du PDF', 'error');
    }
}

// Exposer les fonctions utiles globalement
window.anecoop = {
    showToast,
    exportToCSV,
    exportToExcel,
    exportToPDF,
    validateInput,
    isValidEmail,
    isValidPhone,
    isValidDate,
    addNotification
};