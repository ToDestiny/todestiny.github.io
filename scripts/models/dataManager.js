import recipes from '../../data/recipes.js';

export default class dataManager {
    //Initialisation des data
    static getData() {
        this.data = recipes;
        this.filteredData = recipes;
    }

    //Récupération des ingredients
    static getIngredients() {
        const duplicatesIngredients = this.filteredData
            .map((recipe) => recipe.ingredients)
            .flat()
            .map((item) =>
                item['ingredient']
                    .toLowerCase()
                    .trim()
                    .replace(/(^|\s)\S/, (L) => L.toUpperCase())
            )
            .sort();
        this.ingredients = [...new Set(duplicatesIngredients)];
        this.filteredIngredients = [...this.ingredients];
    }

    //Récupération des appareils
    static getAppliances() {
        const duplicatesAppliances = this.filteredData
            .map((recipe) => recipe.appliance.trim())
            .sort();
        this.appliances = [...new Set(duplicatesAppliances)];
        this.filteredAppliances = [...this.appliances];
    }

    //Récupération des ustensiles
    static getUstensils() {
        const duplicatesUstensils = this.filteredData
            .map((recipe) => recipe.ustensils)
            .flat()
            .sort();
        this.ustensils = [...new Set(duplicatesUstensils)];
        this.filteredUstensils = [...this.ustensils];
    }

    //Initialisation du tableau destiné à contenir les badges
    static setBadgeItems() {
        this.badgeItems = [];
    }

    //Recherche via TITRE, INGREDIENTS, DESCRIPTION avec la searchBar
    static filterData(term) {
        //  Recherche avec la fonction JavaScript Filter
        this.filteredData = this.filteredData.filter(
            (recipe) =>
                recipe.name.toLowerCase().includes(term) ||
                recipe.description.toLowerCase().includes(term) ||
                recipe.ingredients.some((ingredient) =>
                    ingredient.ingredient.includes(term)
                )
        );
    }

    //Recherche ingredient dans le sous-menu filtre avancé
    static filterIngredients(term) {
        this.filteredIngredients = this.ingredients.filter((ingredient) =>
            ingredient.toLowerCase().includes(term)
        );
    }

    //Recherche appareil dans le sous-menu filtre avancé
    static filterAppliances(term) {
        this.filteredAppliances = this.appliances.filter((appliance) =>
            appliance.toLowerCase().includes(term)
        );
    }

    //Recherche ustensile dans le sous-menu filtre avancé
    static filterUstensils(term) {
        this.filteredUstensils = this.ustensils.filter((ustensil) =>
            ustensil.toLowerCase().includes(term)
        );
    }

    //Filtrage des data via les badges
    static filterWithBadges() {
        this.badgeItems.forEach((badge) => {
            switch (badge.category) {
                case 'ingredients-filter-list':
                    this.filteredData = this.filteredData.filter((recipe) =>
                        recipe.ingredients.some((ingredient) =>
                            ingredient.ingredient
                                .toLowerCase()
                                .includes(badge.name.toLowerCase())
                        )
                    );
                    break;
                case 'appliances-filter-list':
                    this.filteredData = this.filteredData.filter((recipe) =>
                        recipe.appliance
                            .toLowerCase()
                            .includes(badge.name.toLowerCase())
                    );
                    break;
                case 'ustensils-filter-list':
                    this.filteredData = this.filteredData.filter((recipe) =>
                        recipe.ustensils.some((ustensil) =>
                            ustensil
                                .toLowerCase()
                                .includes(badge.name.toLowerCase())
                        )
                    );
                    break;
            }
        });
    }
}
