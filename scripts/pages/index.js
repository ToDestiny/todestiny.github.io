import dataManager from '../models/datamanager.js';
import displayRecipeCard from '../utils/displayRecipeCard.js';

//Initialisation des data
dataManager.getData();

//Affichage de toutes les recettes
displayRecipeCard(dataManager.data);
