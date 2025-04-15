/**
 * Système de Réservation des Formations Anecoop
 * main.js - Fonctionnalités JavaScript communes
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les événements
    initNotifications();
    initModals();
    initThemeToggle();
    initHelpTabs();
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
});

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
}

/**
 * Charge les notifications depuis le stockage local
 */
function loadNotifications() {
    const notificationsList = document.getElementById('notifications-list');
    const notificationsBadge = document.getElementById('notificationsBadge');
    
    if (!notificationsList) return;
    
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
            markNotification(index, !notifications[index].read);
        });
    });
    
    // Marquer toutes comme lues
    notifications.forEach((notification, index) => {
        if (!notification.read) {
            markNotification(index, true);
        }
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
    const submitFeedback = document.getElementById('submitFeedback');
    
    if (feedbackBtn && feedbackModal) {
        feedbackBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(feedbackModal);
            modal.show();
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
            .then(response => response.json())
            .then(data => {
                // Réactiver le bouton
                submitFeedback.disabled = false;
                submitFeedback.innerHTML = '<i class="fas fa-paper-plane"></i> Envoyer';
                
                if (data.id) {
                    // Réinitialiser le formulaire
                    form.reset();
                    
                    // Fermer la modal
                    bootstrap.Modal.getInstance(feedbackModal).hide();
                    
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
    
    if (helpBtn && helpModal) {
        helpBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(helpModal);
            modal.show();
        });
    }
}

/**
 * Initialise le toggle de thème
 */
function initThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    
    if (themeToggle) {
        // Vérifier le thème sauvegardé
        const savedTheme = localStorage.getItem('anecoop-theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-mode');
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
        }
        
        // Gérer le changement de thème
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            
            if (document.body.classList.contains('dark-mode')) {
                themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                localStorage.setItem('anecoop-theme', 'dark');
            } else {
                themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
                localStorage.setItem('anecoop-theme', 'light');
            }
        });
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
            }
        });
    });
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
    let bgColor = '#63b3ed'; // info (par défaut)
    
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
    }
    
    // Afficher la notification avec Toastify
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
}