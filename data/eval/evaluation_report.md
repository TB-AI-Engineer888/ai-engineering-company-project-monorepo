# HealthCore revenue model evaluation

The target is `revenue_usd` on the `consolidated` rows in `data/raw/healthcore_sales.csv`. No patient identifier, diagnosis, or clinical field is used.

## 1. Does the model show underfitting, overfitting, or is it reasonably well fitted?

The model is **overfitting**.

The learning curve uses only 2016-2023. Training months are added from the start of that series, and the last 12 months of 2023 stay the validation block. At 72 training months the training RMSE is 54550 USD (1.9% of average monthly training revenue) and the validation RMSE is 195386 USD (7.0%). The training line stays low and the validation line stays higher as the training set grows. That is a wide, persistent gap, which is overfitting. The training error is not high, so this is not underfitting. The two lines do not meet, so the model is not reasonably well fitted.

## 2. How stable is its performance when you change which portion of the data you train on?

Validation RMSE is 164716 ± 25190 USD and validation MAE is 139791 ± 19664 USD across five chronological folds. The lowest validation RMSE is 147207 USD on the window ending 2021-08-01. The highest is 207040 USD on the window ending 2023-12-01. Changing the training portion moves the error, and the latest window is the largest move. The spread is 59832 USD, so the performance is not flat, and it does not jump to a different scale.

## 3. If there is a problem, what is the specific corrective action?

The first change is to stop the trees from memorizing individual months: raise min_samples_leaf from 2 to 6 and lower max_depth from 6 to 4. Do not add depth. The training line is already low, and the gap is the later training months, not a lack of model size.

## Metrics

RMSE is the primary metric. MAE is reported beside it. HealthCore's October-December revenue rises 15-20% and July-August revenue falls 12-18%, while the other months move about ±5%. RMSE penalizes a miss of that seasonal size more than MAE does. MAE is the typical monthly dollar miss. Training MAE is 41968 USD and training RMSE is 54550 USD. Validation MAE is 165839 USD and validation RMSE is 195386 USD.

The plot is `data/eval/learning_curve.png`.
