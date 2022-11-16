import numpy as np
from scipy.sparse import csr_matrix, coo_matrix
from sklearn.preprocessing import MinMaxScaler
from Dataprocessing import mapminmax
from Dataprocessing import load_Data, load_Data2, get_data, Euc_dist, normalize_by_minmax
import datetime
from sklearn.cluster import KMeans
import random
import matplotlib.pyplot as plt

scaler = MinMaxScaler(feature_range=(0, 1))

def random_walk(G, path_length, alpha, rand=random.Random(), start=None):
    """ 
        Pure random walk, using Markov stochastic processes
    """
    if start:
        path = [start]
    else:
        path = [rand.choice(list(G.nodes()))]

    while len(path) < path_length:
        cur = path[-1]
        if G.degree(cur) > 0:
            if rand.random() >= alpha:
                # print(list(G.neighbors(cur)))
                path.append(rand.choice(list(G.neighbors(cur))))
            else:
                path.append(path[0])
        else:
            break
    return [node for node in path]

def random_Walk_ECPCS(similarity_mat, length):
    """
        Python implementation of random walk in 'ECPCS'
        params:
            similarity_mat: similarity matrix
            l: The step size of each random walk
        returns:
            newS:The output similarity matrix
    """
    size_S = similarity_mat.shape[0]
    for i in range(0, size_S):
        similarity_mat[i, i] = 0

    rowSum = np.array(np.transpose(np.sum(similarity_mat, axis=1)))
    rowSum = rowSum.reshape(size_S, 1)
    # print(rowSum)
    rowSums = np.tile(rowSum, size_S)
    find_arr = np.where(rowSums == 0)
    for i in range(0, len(find_arr[0])):
        rowSums[find_arr[0][i]][find_arr[1][i]] = -1.0
    
    P_mat = similarity_mat / rowSums
    find_arr = np.where(P_mat < 0)
    for i in range(0, len(find_arr[0])):
        P_mat[find_arr[0][i]][find_arr[1][i]] = 0.0

    tempP = P_mat
    inProdP = np.dot(P_mat, np.transpose(P_mat))
    for i in range(0, length):
        tempP = np.dot(tempP, P_mat)
        inProdP = inProdP + np.dot(tempP, np.transpose(tempP))

    diag_inProdP = np.array(np.diag(inProdP))
    diag_inProdP = diag_inProdP.reshape(len(inProdP), 1)
    inProdii = np.tile(diag_inProdP, size_S)
    inProdjj = np.transpose(inProdii)
    newS = inProdP / np.sqrt(np.multiply(inProdii, inProdjj))
    sr = np.sum(np.transpose(P_mat), axis=0)
    isolatedIdx = np.array(np.where(sr < 10e-10))
    if len(isolatedIdx) > 0:
        newS[isolatedIdx, :] = 0
        newS[:, isolatedIdx] = 0
    # sr = np.sum(np.transpose(P_mat), axis=0)
    return newS


class Dpcpp:

    def __init__(self, label, data_to_kms, index_return, s, p, l, N, r=150):
        # self.data = data
        self. label = label
        self.s = s
        self.p = p
        self.l = l
        self.r = r
        self.k = len(set(label))
        self.N = 16*N
        self.cluster = [-1] * p
        self.center = [-1] * self.k
        self.sample_label = [-1]*self.N
        self.data_to_kms = data_to_kms
        self.index_return = index_return

    def fit(self):

        similarity_mat, Z= self.sample_Data()
        similarity_mat = random_Walk_ECPCS(similarity_mat, self.l)
        index_return = self.index_return.astype(np.int64)
        rho = self.rho_creator(Z)
        # sim, nneigh = simNeigh_creator(rm_similiarity, rho, p, k)
        sim, nneigh, sort_rho_idx = self.simNeigh_creator(similarity_mat, rho, self.p)
        core_index = [x for (x, y) in enumerate(nneigh) if y == -1]

        nneigh, topK = self.DC_inter_dominance_estimation(rho, nneigh, core_index, sort_rho_idx, similarity_mat)
        if type(topK) == int:
            importance_sorted = self.topK_selection(sim, rho, self.k)
            self.sample_cluster(sort_rho_idx, nneigh)
        
        # self.plot0 = []
        # self.plot1 = []
        # self.plot2 = []
        # self.plot3 = []
        # self.plot4 = []
        # self.plot5 = []
        # self.plot6 = []
        # self.plot7 = []
        # self.plot8 = []
        # self.plot9 = []
        for i in range(0, self.N):
            self.sample_label[i] = self.cluster[index_return[i]]
        #     if self.cluster[index_return[i]] == 0:
        #         self.plot0.append(i)
        #     elif self.cluster[index_return[i]] == 1:
        #         self.plot1.append(i)
        #     elif self.cluster[index_return[i]] == 2:
        #         self.plot2.append(i)
        #     elif self.cluster[index_return[i]] == 3:
        #         self.plot3.append(i)
        #     elif self.cluster[index_return[i]] == 4:
        #         self.plot4.append(i)
        #     elif self.cluster[index_return[i]] == 5:
        #         self.plot5.append(i)
        #     elif self.cluster[index_return[i]]== 6:
        #         self.plot6.append(i)
        #     elif self.cluster[index_return[i]] == 7:
        #         self.plot7.append(i)
        #     elif self.cluster[index_return[i]] == 8:
        #         self.plot8.append(i)
        #     elif self.cluster[index_return[i]] == 9:
        #         self.plot9.append(i)
        # print(nneigh)
        # self.plot_spiral(self.data, self.sample_label)

        return self.sample_label



    def sample_Data(self):

        tmp_minDistance = self.data_to_kms.min(axis=1)   # The minimum distance from each input sample to the Kmeans cluster center
        tmp_index = self.data_to_kms.argmin(axis=1)      # Index of the minimum distance from each input sample to the Kmeans cluster center
        # data_to_kms = data_to_kms[:, shulffle_N[0:self.s]]
        sigma = np.sqrt(np.mean(np.mean(self.data_to_kms)))

        minDistance = np.zeros([self.p, self.r])
        index = np.zeros([self.p, self.r])
        minDistance[:, 0] = tmp_minDistance
        index[:, 0] = tmp_index

        similarity_mat, Z = self.similarity_creator(self.data_to_kms, minDistance, index, sigma)
        similarity_mat = mapminmax(similarity_mat, 1, 0)
        return similarity_mat, Z

    def similarity_creator(self, Eudist_mat, minEudist_mat, minEudist_index, sigma):
        """
            Get the adjacency matrix and the similarity matrix
            params:
                Eudist_mat: distance matrix
                minEudist_mat: mininum distances of the points
                minEudist_index: index of the mininum distances
                sigma: threshold
            returns:
                similarity_mat: similarity matrix
                Z: adjacency matrix
        """
        Eudist_numpy = np.array(Eudist_mat)
        j = 1
        for t in range(0, self.r - 1):
            for i in range(0, Eudist_mat.shape[0]):
                Eudist_numpy[i][int(minEudist_index[i][j - 1])] = 1e10
                minEudist_mat[i][j] = np.min(Eudist_numpy[i])
                minEudist_index[i][j] = np.argmin(Eudist_numpy[i])
            j = j + 1

        minEudist_mat = np.exp(-minEudist_mat / (2 * sigma**2))
        row = np.expand_dims(np.transpose(range(0, self.p)), 1).repeat(self.r, axis=1)
        col = minEudist_index.astype(int)
        Z = coo_matrix((minEudist_mat.flatten(), (row.flatten(), col.flatten())),shape=(self.p, self.s)).toarray()    # Z: adjacency matrix
        Z = np.transpose(Z)
        Z = mapminmax(Z, 1, 0)
        similarity_mat = np.dot(np.transpose(Z), Z)     # similarity_mat: similarity matrix
        return similarity_mat, Z

    def rho_creator(self, Z):
        """
            Get the density of each sample from the adjacency matrix
            params:
                Z: adjacency matrix
            returns:
                rho: density matrix
        """
        rho = np.sum(Z, axis=0)
        rho = mapminmax(rho, 1, 0)
        rho = rho.flatten()
        return rho

    def simNeigh_creator(self, similarity, rho, p):
        """
            Get the ranking of similarity, the nearest neighbour and the ranking of density from the similarity matrix
            params:
                similarity: similarity matrix
                rho: density matrix
            returns:
                sim: the ranking of similarity
                nneigh: the nearest neighbour of every point
                sort_rho_idx: the ranking of density
        """
        sort_rho_idx = np.argsort(-rho)
        sim = [0.0] * p
        nneigh = [-1] * p
        for i in range(1, p):
            for j in range(0, i):
                if similarity[sort_rho_idx[i], sort_rho_idx[j]] > sim[sort_rho_idx[i]]:
                    sim[sort_rho_idx[i]] = similarity[sort_rho_idx[i], sort_rho_idx[j]]
                    nneigh[sort_rho_idx[i]] = sort_rho_idx[j]
        sim[sort_rho_idx[0]] = 1000.0
        for i in range(0, p):
            if sim[sort_rho_idx[0]] > sim[sort_rho_idx[i]]:
                sim[sort_rho_idx[0]] = sim[sort_rho_idx[i]]
        sim = mapminmax(np.array(sim), 1, 0)
        sim = sim.flatten()

        return sim, nneigh, sort_rho_idx

    def topK_selection(self, sim, rho, k):
        """
            Select top-K significant DCs
            Similar to DPC, do importance estimates
            params:
                sim: the ranking of similarity
                rho: density matrix
            returns:
                importance_sorted: the ranking of importances
        """
        importance = []
        for i in range(0, len(sim)):
            sim[np.argmin(sim)] = 0.01
        dist = 1.0 / sim
        # print('dist:',dist)
        # plt.scatter(rho, dist)
        # plt.show()
        for s, d in zip(dist, rho):
            importance.append(d * s)
        importance = np.array(importance).flatten()
        importance_sorted = np.argsort(-importance)
        for i in range(0, k):
            self.cluster[importance_sorted[i]] = i
            self.center[i] = importance_sorted[i]
        return importance_sorted

    def sample_cluster(self, rho_sorted, nneigh):
        """
            Use the topK centers to cluster the modes
            params:
                importance_sorted: the ranking of importances
                nneigh: nearst neighbour of every point
        """
        for i in range(0, self.p):
            if self.cluster[rho_sorted[i]] == -1:
                self.cluster[rho_sorted[i]] = self.cluster[nneigh[rho_sorted[i]]]

    def DC_inter_dominance_estimation(self, rho, ndh, core_index, sort_rho_idx, similarity_mat):
        """
            From yanggeping's FastDEC
            params:
                rho: density matrix
                ndh: nearst density-higher
                core-index: someone has not ndh
                sort_rho_idx: ranking of density
                similarity_mat: similarity matrix
            return:
                topK_idx: the index of topK points
        """
        core_index = np.array(core_index)
        sim = similarity_mat[core_index, :]
        indices = np.argsort(-sim, axis=1)
        sim = np.array(sim)
        sim = np.sort(sim, axis=1)
        sim = sim[:, ::-1]
        num_core = len(core_index)
        g = np.full(num_core, -1, np.float32)
        for q, i in enumerate(core_index):
            for p, j in enumerate(indices[q]):
                if rho[i] < rho[j]:
                    g[q] = sim[q][p]
                    ndh[i] = j
                    break
        topK_idx = 0
        if self.k < num_core:
            for i in range(num_core):
                if g[i] == -1:
                    g[i] = np.max(g)
            g = normalize_by_minmax(g)
            core_density = rho[core_index]
            core_density = normalize_by_minmax(core_density)
            SD = core_density * g
            # i = np.argsort(-SD)[0:self.k]
            topK_idx = core_index[np.argsort(-SD)[0:self.k]]
            label = [-1]*self.N
            count = 0
            for i in topK_idx:
                label[i] = count
                count += 1
            for i in sort_rho_idx:
                if self.cluster[i] == -1:
                    self.cluster[i] = label[ndh[i]]
        return ndh, topK_idx

    def final_cluster(self, cdh_ids, core_idx, density):
        """
            From yanggeping's FastDEC
            Use after 'DC_inter_dominance_estimation'
            params:
                density: density matrix
                cdh_ids: nearst density-higher
                core-indx: someone has not ndh
            return:
                label: the labels of clustering
        """
        label = np.full(self.n, -1, np.int32)
        sorted_density = np.argsort(-density)
        count = 0
        for i in core_idx:
            label[i] = count
            count += 1
        for i in sorted_density:
            if label[i] == -1:
                label[i] = label[cdh_ids[i]]
        return label
    def plot_spiral(self, data, label):
        plt.figure(figsize=[6.40, 5.60])
        print((data[self.plot0, 0], data[self.plot0, 1]))
        plt.scatter(data[self.plot0, 0], data[self.plot0, 1], marker='*', c='#FFA500', alpha=0.5)
        plt.scatter(data[self.plot1, 0], data[self.plot1, 1], marker='*', c='#87CEEB', alpha=0.5)
        plt.scatter(data[self.plot2, 0], data[self.plot2, 1], marker='*', c='#FFB6C1', alpha=0.5)
        plt.scatter(data[self.plot3, 0], data[self.plot3, 1], marker='*', c='#D3D3D3', alpha=0.5)
        plt.scatter(data[self.plot4, 0], data[self.plot4, 1], marker='*', c='#D8BFD8', alpha=0.5)
        plt.scatter(data[self.plot5, 0], data[self.plot5, 1], marker='*', c='#FA8072', alpha=0.5)
        plt.scatter(data[self.plot6, 0], data[self.plot6, 1], marker='*', c='#F08080', alpha=0.5)
        plt.scatter(data[self.plot7, 0], data[self.plot7, 1], marker='*', c='#4B0082', alpha=0.5)
        plt.scatter(data[self.plot8, 0], data[self.plot8, 1], marker='*', c='#DEB887', alpha=0.5)
        plt.scatter(data[self.plot9, 0], data[self.plot9, 1], marker='*', c='#808000', alpha=0.5)


        plt.title('Clustering result')
        plt.show()

def get_prototype(data, s, p):
    N = data.shape[0]
    print(N)
    shulffle_N = np.array(range(0, N))
    np.random.seed(5)
    np.random.shuffle(shulffle_N)
    # The first S of the input data are taken for Kmeans clustering
    kmeans_data = data[shulffle_N[0:s], :]
    kmeans = KMeans(n_clusters=p, max_iter=3,random_state=0).fit(kmeans_data)
    kms_label = kmeans.labels_
    kms_center = kmeans.cluster_centers_    # Centers after kmeans clustering
    data_to_kms = np.zeros((N, p))
    for b in range(0, 100):
        data_tmp = data[(int)(N*b/100):((int)(N*(b+1)/100)),:]
        data_to_kms_ = np.array(Euc_dist(data_tmp, kms_center))  # The distance matrix from each input sample to the Kmeans cluster center
        data_to_kms[(int)(N*b/100):((int)(N*(b+1)/100)), :] = data_to_kms_
    tmp_index2_all = data_to_kms.argmin(axis=1)
    data_to_kms_all = data_to_kms[shulffle_N[0:s], :]
    data_to_kms_all = np.transpose(data_to_kms_all)
    return tmp_index2_all, data_to_kms_all, kms_center

def get_alldist(data, p, tmp_index2_all, kms_center):
    N = data.shape[0]
    # data = dim_reduction(data, 500)  # dimension reduction by PCA
    data_to_kms = np.zeros((N, p))
    for b in range(0, 100):
        data_tmp = data[(int)(N*b/100):((int)(N*(b+1)/100)),:]
        data_to_kms_ = np.array(Euc_dist(data_tmp, kms_center))  # The distance matrix from each input sample to the Kmeans cluster center
        data_to_kms[(int)(N*b/100):((int)(N*(b+1)/100)), :] = data_to_kms_

    tmp_index2_alltmp = data_to_kms.argmin(axis=1)
    # data_to_kms = data_to_kms[shulffle_N[0:self.s], :]
    data_to_kms_alltmp = np.transpose(data_to_kms)
    
    tmp_index2_all = np.r_[tmp_index2_all, tmp_index2_alltmp]
    # data_to_kms_all = np.c_[data_to_kms_all, data_to_kms_alltmp]
    return tmp_index2_all
