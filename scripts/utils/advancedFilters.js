import dataManager from '../models/dataManager.js';
import displayRecipeCard from './displayRecipeCard.js';

//DOM variables
const filterBtns = document.querySelectorAll('.filter-btn-toggle');
const filterInputs = document.querySelectorAll('.filter-input');
const filterLists = document.querySelectorAll('.filter-list');
const badgesContainer = document.querySelector('.badges-container');
const recipesGrid = document.getElementById('grid');
const ingredientsFilterList = document.querySelector(
    '.filter-list--ingredients'
);
const appliancesFilterList = document.querySelector('.filter-list--appliances');
const ustensilsFilterList = document.querySelector('.filter-list--ustensils');
const noResultsText = document.querySelector('.no-results-text');

//Génération id aléatoire pour les items contenus dans les listes filtres avancés
const generateRandomId = () => {
    const prevIds = [];
    const newId = Math.floor(Math.random() * 1001);

    if (!prevIds.find((id) => id === newId)) {
        prevIds.push(newId);
        return newId.toString();
    }
};

//Formatage HTML des éléments contenus dans les data filtres avancés
export const displayFilterListItems = (data) => {
    let filterListHtml = '';

    if (data.length > 0) {
        data.forEach(
            (item) =>
                (filterListHtml += `<li data-item_id="${generateRandomId()}" id="filter--${item
                    .split(' ')
                    .join('_')}" class="filter-list__item">${item}</li>`)
        );
    } else {
        filterListHtml =
            '<li class="filter-list__item filter-list__item--empty">Pas de résultat pour cette recherche...</li>';
    }

    return filterListHtml;
};

//Ajout badge
export const addBadge = (event) => {
    //Création d'un nouvel obj badge content grâce aux infos fournies par le click event
    const newBadge = {
        id: event.target.dataset.item_id,
        name: event.target.textContent,
        category: event.target.parentNode.id,
    };

    //Vérification que le badge n'existe pas déjà
    if (dataManager.badgeItems.find((badge) => badge.name === newBadge.name)) {
        return;
    } else {
        //Ajout du badge dans le dataManager
        dataManager.badgeItems = [...dataManager.badgeItems, newBadge];
    }

    //MAJ des data affichées en fonction des badges actifs
    dataManager.filterWithBadges();

    //Gestion de l'affichage du message d'erreur en fonction des résultats post-filtrage
    !dataManager.filteredData.length
        ? (noResultsText.style.display = 'block')
        : (noResultsText.style.display = '');

    //Affichage des recettes filtrées
    displayRecipeCard(dataManager.filteredData);

    //MAJ des items dans les menus filtres avancés
    updateFilterListData();

    //Affichage du badge
    displayBadges();

    //Reset de l'input text dans les menus filter avancés
    filterInputs.forEach((input) => (input.childNodes[1].value = ''));
};

//Affichage des badges
const displayBadges = () => {
    //Ajustement du layout en fonction de la présence (ou non) de badges
    if (dataManager.badgeItems.length > 0) {
        recipesGrid.style.top = '320px';
        badgesContainer.style.display = 'flex';
    } else {
        recipesGrid.style.top = '270px';
        badgesContainer.style.display = 'none';
    }

    //Génération HTML
    let badgeHtml = '';

    dataManager.badgeItems.map((item) => {
        switch (item.category) {
            case 'ingredients-filter-list':
                badgeHtml += `<div data-badge_id="${item.id}"class="badge badge--ingredient">${item.name} <span class="far fa-times-circle badge__icon"></span></div>`;
                break;
            case 'appliances-filter-list':
                badgeHtml += `<div data-badge_id="${item.id}"class="badge badge--appliance">${item.name} <span class="far fa-times-circle badge__icon"></span></div>`;
                break;
            case 'ustensils-filter-list':
                badgeHtml += `<div data-badge_id="${item.id}"class="badge badge--ustensil">${item.name} <span class="far fa-times-circle badge__icon"></span></div>`;
                break;
        }
    });

    //Insertion HTML
    badgesContainer.innerHTML = badgeHtml;

    //Gestion du click event sur les close icons permettant de supprimer les badges
    const badgeCloseIcons = document.querySelectorAll('.badge__icon');
    badgeCloseIcons.forEach((item) =>
        item.addEventListener('click', removeBadge)
    );
};

//Fermeture badge
export const removeBadge = (event) => {
    //Suppression du badge selectionné dans le dataManager
    dataManager.badgeItems = dataManager.badgeItems.filter(
        (badge) => badge.id !== event.target.parentNode.dataset.badge_id
    );

    //Reset|MAJ des data en fonction de la présence (ou non) de characters dans la searchBar
    dataManager.filteredData = [...dataManager.data];
    if (document.getElementById('search').value.length > 2) {
        dataManager.filterData(document.getElementById('search').value);
    }

    //MAJ des data si existence de badge(s)
    if (dataManager.badgeItems.length > 0) {
        dataManager.filterWithBadges();
    }

    //Affichage des recettes filtrées
    displayRecipeCard(dataManager.filteredData);

    //MAJ des items dans les menus filtres avancés
    updateFilterListData();

    //MAJ de l'UI sans le badge supprimé
    displayBadges();
};

//Fermeture des dropdown menu filtres avancés
export const closeFilterList = (event) => {
    //Affichage des btn permettant d'afficher les menus filtres avancés
    filterBtns.forEach((btn) => {
        btn.style.display = 'block';
    });

    //Masquage des menus filtres avancés
    filterInputs.forEach((input) => {
        input.style.display = 'none';
    });

    filterLists.forEach((list) => (list.style.display = 'none'));

    //Reset des éléments présents dans les searchBar des menus filtres avancés
    filterInputs.forEach((input) => (input.childNodes[1].value = ''));

    //Suppresion de la gestion du click event sur la page permetant de masquer les menu filtres avancés
    document.body.removeEventListener(
        'click',
        closeFilterListWithExternalClick
    );
};

//Fermeture des dropdown menu filtres avancés lors d'un click externe (ajout des exceptions pour certains éléments)
export const closeFilterListWithExternalClick = (event) => {
    //Exception lors du click sur l'icon arrow down des btn menus filtres avancés
    if (event.target.className.includes('down')) {
        return;
    }

    //Exception lors du click sur un item présent dans les listes des menus filtres avancés
    if (event.target.className === 'filter-list__item') {
        return;
    }

    //Exception lors du click sur un badge
    if (event.target.parentNode.dataset.badge_id) {
        return;
    }

    //Exception lors du click sur les btns permettant d'afficher les menus filtres avancés + searchBars présentes dans les menus filtres avancés
    switch (event.target.id) {
        case 'ingredientsBtn':
            break;
        case 'appliancesBtn':
            break;
        case 'ustensilsBtn':
            break;
        case 'filter-input-ingredients':
            break;
        case 'filter-input-appliances':
            break;
        case 'filter-input-ustensils':
            break;
        default:
            closeFilterList();
    }
};

//Recherche dans les filtres avancés
const advancedFilterSearch = (event) => {
    if (event.target.value.length > 2) {
        switch (event.target.id) {
            case 'filter-input-ingredients':
                dataManager.filterIngredients(
                    event.target.value.toLocaleLowerCase()
                );
                ingredientsFilterList.innerHTML = displayFilterListItems(
                    dataManager.filteredIngredients
                );
                break;
            case 'filter-input-appliances':
                dataManager.filterAppliances(
                    event.target.value.toLocaleLowerCase()
                );
                appliancesFilterList.innerHTML = displayFilterListItems(
                    dataManager.filteredAppliances
                );
                break;
            case 'filter-input-ustensils':
                dataManager.filterUstensils(
                    event.target.value.toLocaleLowerCase()
                );
                ustensilsFilterList.innerHTML = displayFilterListItems(
                    dataManager.filteredUstensils
                );
                break;
        }

        const filterListItems = document.querySelectorAll('.filter-list__item');
        filterListItems.forEach((item) =>
            item.addEventListener('click', addBadge)
        );
    } else {
        updateFilterListData();
    }
};

//Ouverture des menus filtres avancés
export const showFilterList = (event) => {
    //Fermeture du dropdown menu actuellement ouvert (si besoin)
    closeFilterList();

    //DOM variables
    let currentFilterBtnToggle, currentFilterInput, currentFilterList;

    if (event.target.id.includes('Btn')) {
        currentFilterBtnToggle = event.target;
        currentFilterInput = currentFilterBtnToggle.nextElementSibling;
        currentFilterList = currentFilterInput.nextElementSibling;
    } else if (event.target.className.includes('down')) {
        currentFilterBtnToggle = event.target.parentNode;
        currentFilterInput = currentFilterBtnToggle.nextElementSibling;
        currentFilterList = currentFilterInput.nextElementSibling;
    } else {
        return;
    }

    //Affichage du dropdown menu associé au btn clické
    currentFilterBtnToggle.style.display = 'none';
    currentFilterInput.style.display = 'flex';
    currentFilterList.style.display = 'grid';

    //Gestion de l'input event afin d'effectuer une recherche dans les filtres avancés
    currentFilterInput.addEventListener('input', advancedFilterSearch);

    //Gestion du click event sur la page permetant de masquer les menu filtres avancés
    document.body.addEventListener('click', closeFilterListWithExternalClick);
};

//MAJ des data contenus dans les filtres avancés après recherche effectuée dans la barre de recherche ou ajout de badge(s)
export const updateFilterListData = () => {
    //Récupération des data
    dataManager.getIngredients();
    dataManager.getAppliances();
    dataManager.getUstensils();

    //Génération + insertion du HTML
    ingredientsFilterList.innerHTML = displayFilterListItems(
        dataManager.ingredients
    );
    appliancesFilterList.innerHTML = displayFilterListItems(
        dataManager.appliances
    );
    ustensilsFilterList.innerHTML = displayFilterListItems(
        dataManager.ustensils
    );

    //Gestion du click event sur les filter items permettant d'afficher les badges
    const filterListItems = document.querySelectorAll('.filter-list__item');
    filterListItems.forEach((item) => item.addEventListener('click', addBadge));
};
