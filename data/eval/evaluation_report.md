# HealthCore revenue model evaluation

The model is **overfitting**.

The learning curve uses only 2016-2023. The last 12 of those months are the validation block, and the earlier months are added from the start of the series. At the full training size the training RMSE is 1.9% of average monthly training revenue and the validation RMSE is 7.0%. The seasonal moves in the briefing are a 12-18% summer drop and a 15-20% October-December rise, so this error is smaller than those moves.

Five chronological folds, validation RMSE 164716 ± 25190 USD and validation MAE 139791 ± 19664 USD. No fold is shuffled, and each later validation block starts after the previous one.

RMSE is the primary metric. A large miss in July-August or October-December costs HealthCore more than a small miss, because those seasons move revenue by 12-20 percent. MAE is the typical monthly dollar miss and is reported beside it. On the final training fit, training MAE is 41968 USD and training RMSE is 54550 USD. Validation MAE is 165839 USD and validation RMSE is 195386 USD.

## Corrective action

The first change is to stop the trees from memorizing individual months: raise min_samples_leaf from 2 to 6 and lower max_depth from 6 to 4. Do not add depth. The training line is already low, and the gap is the later training months, not a lack of model size.

No patient-level fields are used. The series remains the consolidated monthly revenue in `data/raw/healthcore_sales.csv`.
