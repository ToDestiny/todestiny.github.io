import dataManager from '../models/dataManager.js';
import displayRecipeCard from '../utils/displayRecipeCard.js';
import {
    showFilterList,
    closeFilterList,
    updateFilterListData,
} from '../utils/advancedFilters.js';

//DOM variables
const searchTerm = document.getElementById('search');
const noResultsText = document.querySelector('.no-results-text');
const filterBtns = document.querySelectorAll('.filter-btn-toggle');
const filterBtnIcons = document.querySelectorAll('.filter-btn-toggle__icon');
const filterInputBtns = document.querySelectorAll('.filter-input__btn');

//Initialisation des data
dataManager.getData();
dataManager.setBadgeItems();

//Affichage de toutes les recettes
displayRecipeCard(dataManager.data);

//MAJ des items dans les menus filtres avancés
updateFilterListData();

//Gestion de l'input event dans la searchBar
function handleInputChange(event) {
    if (event.target.value.length > 2) {
        //Reset|MAJ des data si existence de badge(s)
        dataManager.filteredData = [...dataManager.data];
        if (dataManager.badgeItems.length > 0) {
            dataManager.filterWithBadges();
        }

        //Récupération des data filtrées
        dataManager.filterData(event.target.value.toLocaleLowerCase());
        console.log(dataManager.filteredData);

        //Gestion de l'affichage du message d'erreur en fonction des résultats post-filtrage
        !dataManager.filteredData.length
            ? (noResultsText.style.display = 'block')
            : (noResultsText.style.display = '');

        //Affichage des recettes filtrées
        displayRecipeCard(dataManager.filteredData);

        //MAJ des items dans les menus filtres avancés
        updateFilterListData();
    } else {
        //Masquage du message d'erreur
        noResultsText.style.display = '';

        //Reset|MAJ des data en fonction de la présence (ou non) de badges
        dataManager.filteredData = [...dataManager.data];
        if (dataManager.badgeItems.length > 0) {
            dataManager.filterWithBadges();
        }

        //Affichage des data filtrées
        displayRecipeCard(dataManager.filteredData);

        //MAJ des items dans les menus filtres avancés
        updateFilterListData();
    }
}
searchTerm.addEventListener('input', handleInputChange);

//Gestion du click event sur les btn permetant d'afficher les menu filtres avancés
filterBtns.forEach((btn) => btn.addEventListener('click', showFilterList));
filterBtnIcons.forEach((btn) => btn.addEventListener('click', showFilterList));

//Gestion du click event sur les btn permetant de masquer les menu filtres avancés
filterInputBtns.forEach((btn) =>
    btn.addEventListener('click', closeFilterList)
);
