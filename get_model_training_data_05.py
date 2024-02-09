from datetime import datetime, date
import warnings

import pandas
import numpy as np
import holidays
import statsmodels.api as sm
from statsmodels.othermod.betareg import BetaModel
from statsmodels.tools.sm_exceptions import HessianInversionWarning, ConvergenceWarning
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.utils.validation import check_is_fitted, check_array


def get_features_and_data(data_csv="troon_instagram_clean_post_data.csv"):
    df = pandas.read_csv(data_csv)
    df = df.set_index("id")
    df = df[["post_month", "post_day", "post_year", "days_since_previous_release", "release_post"]].copy()
    df["month"] = df["post_month"].apply(lambda x : datetime.strptime(x, '%B').month)
    df = df.rename(columns={"post_year" : "year", "post_day" : "day"})
    df["date"] = pandas.to_datetime(df[["year", "month", "day"]])
    del df["post_month"]
    del df["day"]
    del df["month"]
    
    df = df[df["release_post"] == True].copy()
    df = df[df["days_since_previous_release"] != 0].copy()

    years = set(df["year"])
    nj_holidays = holidays.UnitedStates(state="NJ", years=years)
    nj_holidays.append({"{}-03-17".format(y) : "St. Patrick's Day" for y in years})
    nj_holidays.append({"{}-02-14".format(y) : "Valentine's Day" for y in years})
    del df["year"]

    # Super Bowls count as holidays as far as beer is concerned lol
    nj_holidays["2016-02-07"] = "Super Bowl 50"
    nj_holidays["2017-02-05"] = "Super Bowl LI"
    nj_holidays["2018-02-04"] = "Super Bowl LII"
    nj_holidays["2019-02-03"] = "Super Bowl LIII"
    nj_holidays["2020-02-02"] = "Super Bowl LIV"
    nj_holidays["2021-02-07"] = "Super Bowl LV"
    nj_holidays["2022-02-13"] = "Super Bowl LVI"
    nj_holidays["2023-02-12"] = "Super Bowl LVII"
    nj_holidays["2024-02-11"] = "Super Bowl LVIII"

    df = df.sort_values(by=["date"]).set_index("date")
    daily = pandas.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(daily, method=None)
    df["release_post"] = df["release_post"].fillna(False)

    df = df.reset_index()
    release_dates = list(df[df["release_post"] == True]["index"])
    df["closest_release_date"] = df["index"].apply(lambda x : max([d for d in release_dates if d <= x]))

    df["backfill"] = (df["index"] - df["closest_release_date"]).values.astype("timedelta64[D]").astype(float)
    df["days_since_previous_release"] = df["days_since_previous_release"].fillna(df["backfill"])
    del df["backfill"]
    del df["closest_release_date"]

    df["future_release_date"] = df["index"].apply(lambda x : min([d for d in release_dates if d >= x]))
    df["days_until_next_release"] = (df["future_release_date"] - df["index"]).values.astype("timedelta64[D]").astype(float)
    del df["future_release_date"]

    df["prob_of_release"] = (df["days_since_previous_release"] /
                             (df["days_since_previous_release"] + df["days_until_next_release"]))
    del df["days_until_next_release"]

    df = _get_features(df.copy(), nj_holidays)
    df = df[df["prob_of_release"].notnull()].copy()

    train_df = df[0:int(len(df) * 0.90)].copy()
    test_df = df[~df.index.isin(train_df.index)].copy()
    print(f"training examples = {len(train_df)}, testing examples = {len(test_df)}")

    features = [c for c in df.columns if c not in ["index", "prob_of_release", "release_post"]]

    last_release_date = test_df[test_df["prob_of_release"] == 1][-1:].iloc[0]["index"]
    next_month = pandas.DataFrame([{"index" : t} for t in 
                                   pandas.date_range(start=last_release_date, freq="1D", periods=31)])
    next_month = next_month[1:].copy()
    next_month["days_since_previous_release"] = range(1, len(next_month) + 1)
    next_month["previous_release_post"] = [1] + [0] * 29
    next_month = _get_features(next_month, nj_holidays)
    next_month = next_month[next_month["index"] >= pandas.Timestamp(date.today())].copy()
    
    for f in features:
        if f not in next_month.columns:
            next_month[f] = 0

    return (df, train_df, test_df, features, next_month)


def _get_features(df, nj_holidays):
    # in addition to days_since_previous_release
    
    df["month_holidays"] = df["index"].apply(
        lambda x : len([h for h in nj_holidays if h.month == x.month and h.year == x.year]))
    
    df["weekday"] = df["index"].apply(lambda x : x.strftime("%A"))
    df["month"] = df["index"].apply(lambda x : x.strftime("%b"))
    
    df = pandas.get_dummies(df, columns=["weekday"], prefix="WD")
    df = pandas.get_dummies(df, columns=["month"], prefix="M")
    
    if "previous_release_post" not in df.columns:
        df["previous_release_post"] = df["release_post"].shift().fillna(False)
        df["previous_release_post"] = df["previous_release_post"].apply(int)
        del df["release_post"]
    
    return df


def weighted_absolute_percentage_error(Y_expected, Y_pred):
    if isinstance(Y_expected, list):
        Y_expected = np.array(Y_expected)
    if isinstance(Y_pred, list):
        Y_pred = np.array(Y_pred)

    absolute_errors = np.abs(Y_expected - Y_pred)
    error_sum = np.sum(absolute_errors)

    return error_sum / np.sum(Y_expected)


class BetaRegression(BaseEstimator, RegressorMixin):
    def __init__(self, fit_intercept=True):
        self.fit_intercept = fit_intercept


    def fit(self, X, y):
        X_temp, y = self._validate_data(
            X, y, accept_sparse=False, y_numeric=True, multi_output=True
        )
        X = pandas.DataFrame(X_temp, columns=X.columns, index=X.index)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=HessianInversionWarning)
            warnings.simplefilter("ignore", category=ConvergenceWarning)
            if self.fit_intercept:
                self.beta_ = BetaModel(y, sm.add_constant(X, has_constant="add"))
            else:
                self.beta_ = BetaModel(y, X)
            self.model_ = self.beta_.fit()

        coefs = self.model_.params.copy()
        if self.fit_intercept:
            self.intercept_ = coefs["const"]
            del coefs["const"]
        del coefs["precision"]
        self.feature_names_in_ = list(coefs.index)
        self.coef_ = coefs.values
        self.n_features_in_ = len(coefs)


    def predict(self, X):
        check_is_fitted(self, "model_")

        # Input validation
        X = check_array(X)
        
        if self.fit_intercept:
            X = sm.add_constant(X, has_constant="add")

        return self.model_.predict(X)


    def get_params(self, deep=False):
        return {"fit_intercept" : self.fit_intercept}
