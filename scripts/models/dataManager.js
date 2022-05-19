import recipes from '../../data/recipes.js';

export default class dataManager {
    //Initialisation des data
    static getData() {
        this.data = recipes;
        this.filteredData = recipes;
    }
}
