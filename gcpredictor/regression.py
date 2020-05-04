from sklearn.linear_model import LinearRegression

class CustomLinearRegression(LinearRegression):
    def predict(self, X):
        return super().predict(X)
