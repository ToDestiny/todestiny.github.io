//DOM variables
const recipeGrid = document.getElementById('grid');

//Affichage recette sous forme de carte
const displayRecipeCard = (data) => {
    let gridContent = '';

    data.forEach((recipe) => {
        let ingredientListHtml = '';

        //Mise en forme de l'affichage des ingredients
        recipe.ingredients.forEach((ingredient) => {
            let formatedIngredientQuantity = ingredient.quantity
                ? `: ${ingredient.quantity}`
                : '';
            let formatedUnit = ingredient.unit ? ingredient.unit : '';
            let separator;

            if (formatedUnit.length === 0 || formatedUnit.length < 3) {
                separator = '';
            } else {
                separator = ' ';
            }

            ingredientListHtml += `<li class="recipe-ingredient"><span class="recipe-ingredient__name">${ingredient.ingredient}</span>${formatedIngredientQuantity}${separator}${formatedUnit}</li>`;
        });

        //Génération du HTML pour chaque carte
        return (gridContent += `<article data-id="${recipe.id}" class="recipe-card">
                                    <div class="recipe-card__img-container"></div>
                                    <div class="recipe-card__text-container">
                                        <h2 class="recipe-title">${recipe.name}</h2>
                                        <div class="recipe-time"><i class="far fa-clock recipe-time__icon"></i> ${recipe.time} min</div>
                                        <div class="recipe-ingredients">
                                            <ul>
                                                ${ingredientListHtml}
                                            </u>
                                        </div>
                                        <p class="recipe-description">${recipe.description}</p>
                                    </div>
                                </article>`);
    });

    recipeGrid.innerHTML = gridContent;
};

export default displayRecipeCard;
