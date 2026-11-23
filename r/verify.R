# Independent check of the Python results in base R (+ MASS, jsonlite).
#
# Input : data/processed/returns_<name>.csv   (written by python/run_all.py)
#         results/tables/summary_<name>.json  (Python's numbers)
# Output: results/tables/r_check_<name>.csv   (one row per quantity: python, R, diff, pass)
# Exit  : status 1 if any check fails, so it can be used as a test.
#
# Run from the repo root:  Rscript r/verify.R 2330_TW
#
# Only the CSV of returns is shared between the languages; every statistic is
# recomputed here from that CSV with R's own functions (shapiro.test,
# Box.test, MASS::fitdistr, binom.test) or written out from the formula.

suppressPackageStartupMessages({ library(jsonlite); library(MASS) })

args <- commandArgs(trailingOnly = TRUE)
name <- if (length(args)) args[1] else "2330_TW"
ret_file <- file.path("data", "processed", paste0("returns_", name, ".csv"))
sum_file <- file.path("results", "tables", paste0("summary_", name, ".json"))
if (!file.exists(ret_file)) stop("missing ", ret_file, " - run python/run_all.py first")

d   <- read.csv(ret_file, stringsAsFactors = FALSE)
py  <- fromJSON(sum_file)
cfg <- fromJSON("config.json")

stopifnot(!anyNA(d$ret), !any(duplicated(d$date)))
tr <- d$ret[d$sample == "train"]
te <- d$ret[d$sample == "test"]

mom <- function(r) {
  n <- length(r); x <- r - mean(r)
  m2 <- mean(x^2); m3 <- mean(x^3); m4 <- mean(x^4)
  g1 <- m3 / m2^1.5; g2 <- m4 / m2^2 - 3
  jb <- n / 6 * (g1^2 + g2^2 / 4)
  list(n = n, mean = mean(r), sd = sd(r), skew = g1, excess_kurtosis = g2, jb = jb)
}

rows <- list()
add <- function(what, p, r, tol, rel = FALSE) {
  diff <- if (rel) abs(p / r - 1) else abs(p - r)
  rows[[length(rows) + 1]] <<- data.frame(check = what, python = p, R = r, diff = diff,
                                           tol = tol, pass = diff <= tol)
}

# 1. moments and Jarque-Bera on the train sample
mr <- mom(tr); mp <- py$moments$train
add("n_train", mp$n, mr$n, 0)
add("n_test", py$moments$test$n, length(te), 0)
for (k in c("mean", "sd", "skew", "excess_kurtosis", "jb")) add(paste0("train_", k), mp[[k]], mr[[k]], 1e-9, rel = TRUE)

# 2. Shapiro-Wilk (different implementations -> loose tolerance on W)
sw <- shapiro.test(tr)
add("shapiro_W", py$shapiro_train$W, unname(sw$statistic), 1e-4)

# 3. Ljung-Box on squared demeaned returns (volatility clustering)
lb <- Box.test((tr - mean(tr))^2, lag = 10, type = "Ljung-Box")
add("ljung_box_Q", py$ljung_box_sq_train$Q, unname(lb$statistic), 1e-6, rel = TRUE)

# 4. Student-t fit: independent optimiser, so compare df with a loose tolerance
ft <- suppressWarnings(fitdistr(tr, "t"))
add("t_df", py$t_fit_train$df, unname(ft$estimate["df"]), 0.05, rel = TRUE)
add("t_scale", py$t_fit_train$scale, unname(ft$estimate["s"]), 0.01, rel = TRUE)

# 5. fixed-SD exceedance in the test sample
mu <- mean(tr); s <- sd(tr)
wilson <- function(x, n, z = qnorm(0.975)) {
  p <- x / n; den <- 1 + z^2 / n; c <- (p + z^2 / (2 * n)) / den
  h <- z * sqrt(p * (1 - p) / n + z^2 / (4 * n^2)) / den
  c(max(0, c - h), min(1, c + h))
}
ex <- py$exceedance
for (i in seq_len(nrow(ex))) {
  k <- ex$k[i]
  hits <- sum(te < mu - k * s | te > mu + k * s)
  add(sprintf("k%d_test_hits", k), ex$test_hits[i], hits, 0)
  add(sprintf("k%d_p_normal", k), ex$p_normal[i], 2 * pnorm(-k), 1e-12)
  add(sprintf("k%d_wilson_low", k), ex$ci95_low[i], wilson(hits, length(te))[1], 1e-12)
  add(sprintf("k%d_binom_p_vs_normal", k), ex$binom_p_vs_normal[i],
      binom.test(hits, length(te), 2 * pnorm(-k))$p.value, 1e-8)
}

# 6. rolling-SD exceedance
w <- cfg$rolling_window; all <- d$ret; nt <- length(tr)
z <- sapply((nt + 1):length(all), function(i) { p <- all[(i - w):(i - 1)]; (all[i] - mean(p)) / sd(p) })
ro <- py$exceedance_rolling
for (i in seq_len(nrow(ro))) add(sprintf("roll_k%d_hits", ro$k[i]), ro$test_hits[i], sum(abs(z) > ro$k[i]), 0)

out <- do.call(rbind, rows)
dir.create(file.path("results", "tables"), showWarnings = FALSE, recursive = TRUE)
write.csv(out, file.path("results", "tables", paste0("r_check_", name, ".csv")), row.names = FALSE)
print(out[, c("check", "python", "R", "diff", "pass")], digits = 6, row.names = FALSE)
cat(sprintf("\n%d / %d checks passed\n", sum(out$pass), nrow(out)))
writeLines(capture.output(sessionInfo()), file.path("r", "sessionInfo.txt"))
if (!all(out$pass)) quit(status = 1)
